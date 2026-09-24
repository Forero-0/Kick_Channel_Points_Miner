import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from loguru import logger

from localization import t
from utils.drops_api import DropsAPI


# Statuses Kick reports in /drops/progress. Anything not listed here is
# treated as "still needs watching" so an unknown status never makes the
# miner silently skip a campaign.
STATUS_CLAIMED = "claimed"
STATUS_IN_PROGRESS = "in progress"
DEFAULT_TARGET_MINUTES = 120

# Outcomes of DropsMiner._verify_current()
VERDICT_OK = "ok"
VERDICT_RECONNECT = "reconnect"
VERDICT_SWITCH = "switch"


@dataclass
class DropCampaignTarget:
    """One campaign the user asked to mine, plus its runtime state."""
    campaign_id: str
    name: str
    game: str
    category_id: Optional[int]
    is_global: bool
    target_minutes: int
    channels: List[str]

    # Runtime state (never persisted: Kick is the source of truth)
    progress_units: int = 0
    done: bool = False
    tried: List[str] = field(default_factory=list)
    reward_lines: List[dict] = field(default_factory=list)


@dataclass
class DropsSession:
    """What the miner is watching right now for drops."""
    slug: str
    campaign_id: str
    stream_id: Optional[int]
    channel_id: Optional[int]
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DropsMiner:
    """
    Mines Kick drops for ONE account.

    How it differs from the reference project (KickDropsMiner):

      * No browser. "Watching" is done by the account's existing
        KickWebSocket, exactly like channel points, so this class only
        decides WHICH channel to watch and WHEN to switch.
      * Kick's own /drops/progress is the source of truth. The reference
        kept a local timer that kept running even when Kick was not
        counting anything, and always started from 0 minutes.
      * Already-claimed campaigns are skipped and the remaining minutes
        are derived from real progress.
      * Nothing is persisted; a restart just asks Kick again.

    Kick only credits drops for one stream at a time, so this keeps a
    single active drops session per account.

    The account worker injects two callbacks so this class stays free of
    WebSocket details:

      start_watching(slug, stream_id, channel_id) -> awaitable[bool]
      stop_watching(slug)                         -> awaitable[None]
    """

    def __init__(
        self,
        alias: str,
        token: str,
        drops_cfg: dict,
        proxy: Optional[str] = None,
        check_interval: int = 300,
    ):
        self.alias = alias
        self.token = token
        self.proxy = proxy

        self.campaign_filters: List[str] = [
            str(x).strip().lower()
            for x in drops_cfg.get("campaigns", [])
            if str(x).strip()
        ]
        self.games_filter: List[str] = [
            str(x).strip().lower()
            for x in drops_cfg.get("games", [])
            if str(x).strip()
        ]
        self.auto_claim: bool = bool(drops_cfg.get("auto_claim", False))
        self.max_global_streamers: int = int(
            drops_cfg.get("max_global_streamers", 24)
        )
        self.check_interval = max(60, int(
            drops_cfg.get("check_interval", check_interval)
        ))
        self.offline_checks_to_switch: int = max(1, int(
            drops_cfg.get("offline_checks_to_switch", 2)
        ))

        self.api = DropsAPI(token, proxy=proxy)

        self.targets: Dict[str, DropCampaignTarget] = {}
        self.session: Optional[DropsSession] = None

        self._start_cb: Optional[Callable] = None
        self._stop_cb: Optional[Callable] = None
        self._offline_strikes = 0
        self._running = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------ wiring

    def bind(self, start_watching: Callable, stop_watching: Callable):
        self._start_cb = start_watching
        self._stop_cb = stop_watching

    @property
    def is_watching(self) -> bool:
        return self.session is not None

    @property
    def watching_slug(self) -> Optional[str]:
        return self.session.slug if self.session else None

    # -------------------------------------------- campaign discovery/select

    def _matches_filters(self, campaign: dict) -> bool:
        """
        A campaign is selected when the user listed its id, its name or
        its game. With no filters at all, every active campaign is
        selected.
        """
        if not self.campaign_filters and not self.games_filter:
            return True

        cid = str(campaign.get("id") or "").lower()
        name = str(campaign.get("name") or "").lower()
        game = str(campaign.get("game") or "").lower()

        for f in self.campaign_filters:
            if f == cid or f in name:
                return True
        for g in self.games_filter:
            if g == game or g in game:
                return True
        return False

    @staticmethod
    def _target_minutes(rewards: List[dict]) -> int:
        """
        Rewards are usually cumulative tiers (30 -> 60 -> 120), so the
        campaign is only fully done at the LARGEST tier.
        """
        units = [
            r.get("required_units") or 0 for r in rewards
        ]
        best = max(units) if units else 0
        return int(best) if best > 0 else DEFAULT_TARGET_MINUTES

    async def refresh_campaigns(self) -> bool:
        """
        Rebuild `self.targets` from Kick. Returns False when Kick could
        not be reached (the caller keeps whatever it had before).
        """
        campaigns = await asyncio.to_thread(self.api.get_campaigns)
        if campaigns is None:
            return False

        progress = await asyncio.to_thread(self.api.get_progress)
        if progress is None:
            # Public list worked but the authenticated one didn't. Carry
            # on with "no progress known" instead of dropping everything,
            # and say so: it usually means the token is expired.
            logger.warning(t("drops_progress_unavailable", alias=self.alias))
            progress = []

        progress_by_id = {p["id"]: p for p in progress if p.get("id")}

        new_targets: Dict[str, DropCampaignTarget] = {}
        for c in campaigns:
            if not c.get("id"):
                continue
            if DropsAPI.is_expired(c):
                continue
            if not self._matches_filters(c):
                continue

            prog = progress_by_id.get(c["id"])
            status = (prog or {}).get("status", "not_started")

            # Category: campaigns now carry it themselves; progress is
            # only a fallback for it.
            category_id = c.get("category_id") or (
                (prog or {}).get("category_id")
            )

            prev = self.targets.get(c["id"])
            target = DropCampaignTarget(
                campaign_id=c["id"],
                name=c["name"],
                game=c["game"],
                category_id=category_id,
                is_global=not c["channels"],
                target_minutes=self._target_minutes(c["rewards"]),
                channels=[ch["slug"] for ch in c["channels"]],
                tried=prev.tried if prev else [],
            )

            if prog:
                target.progress_units = int(prog.get("progress_units") or 0)
                target.reward_lines = prog.get("rewards") or []

            # Done when Kick says the whole campaign is claimed, or when
            # every reward we know about is claimed.
            all_claimed = bool(target.reward_lines) and all(
                r.get("claimed") for r in target.reward_lines
            )
            target.done = (status == STATUS_CLAIMED) or all_claimed

            new_targets[c["id"]] = target

        self.targets = new_targets
        return True

    def pending_targets(self) -> List[DropCampaignTarget]:
        """
        Campaigns still worth watching, in the order the user listed
        them (so the config order works as a priority, like streamers).
        """
        pending = [t_ for t_ in self.targets.values() if not t_.done]

        def priority(target: DropCampaignTarget) -> int:
            for idx, f in enumerate(self.campaign_filters):
                if f == target.campaign_id.lower() or f in target.name.lower():
                    return idx
            base = len(self.campaign_filters)
            for idx, g in enumerate(self.games_filter):
                if g == target.game.lower() or g in target.game.lower():
                    return base + idx
            return base + len(self.games_filter)

        pending.sort(key=priority)
        return pending

    # ------------------------------------------------------ channel choice

    async def _live_candidates(
        self, target: DropCampaignTarget
    ) -> List[str]:
        """Channels that could currently earn this campaign."""
        if target.is_global:
            if not target.category_id:
                logger.warning(t(
                    "drops_global_no_category",
                    alias=self.alias, campaign=target.name,
                ))
                return []
            return await asyncio.to_thread(
                self.api.get_live_streamers,
                target.category_id, self.max_global_streamers,
            )
        return list(target.channels)

    async def _pick_channel(
        self, target: DropCampaignTarget, exclude: Optional[str] = None
    ) -> Optional[dict]:
        """
        First live channel of the campaign that is still in the right
        category, skipping the ones already tried in this cycle.
        Returns {"slug", "stream_id", "channel_id"} or None.
        """
        candidates = await self._live_candidates(target)
        if not candidates:
            return None

        # Every candidate tried -> start a fresh cycle instead of
        # dead-locking (same idea as `tried_channels` in the reference).
        if all(c in target.tried or c == exclude for c in candidates):
            target.tried.clear()

        for slug in candidates:
            if slug == exclude or slug in target.tried:
                continue

            state = await asyncio.to_thread(
                self.api.get_channel_state, slug
            )
            await asyncio.sleep(random.uniform(0.8, 2.0))

            if state is None:
                # Blocked/failed: unknown, NOT "live". Try the next one.
                continue
            if not state["is_live"] or not state["stream_id"]:
                continue
            if (
                target.category_id
                and state["category_id"]
                and state["category_id"] != target.category_id
            ):
                logger.debug(t(
                    "drops_wrong_category",
                    alias=self.alias, streamer=slug,
                ))
                continue
            if not state["channel_id"]:
                continue

            return {
                "slug": slug,
                "stream_id": state["stream_id"],
                "channel_id": state["channel_id"],
            }
        return None

    # -------------------------------------------------- start / stop watch

    async def _begin(
        self, target: DropCampaignTarget, exclude: Optional[str] = None
    ) -> bool:
        choice = await self._pick_channel(target, exclude=exclude)
        if not choice:
            return False

        ok = False
        if self._start_cb:
            ok = await self._start_cb(
                choice["slug"], choice["stream_id"], choice["channel_id"],
            )
        if not ok:
            target.tried.append(choice["slug"])
            return False

        target.tried.append(choice["slug"])
        self.session = DropsSession(
            slug=choice["slug"],
            campaign_id=target.campaign_id,
            stream_id=choice["stream_id"],
            channel_id=choice["channel_id"],
        )
        self._offline_strikes = 0

        logger.success(t(
            "drops_now_watching",
            alias=self.alias, streamer=choice["slug"],
            campaign=target.name, game=target.game,
        ))
        return True

    async def _end(self, reason: str = ""):
        if not self.session:
            return
        slug = self.session.slug
        self.session = None
        if self._stop_cb:
            try:
                await self._stop_cb(slug)
            except Exception as e:
                logger.debug(f"drops stop callback error: {e}")
        logger.info(t(
            "drops_stopped_watching",
            alias=self.alias, streamer=slug, reason=reason,
        ))

    # ------------------------------------------------------------ claiming

    async def _maybe_claim(self, target: DropCampaignTarget):
        """
        Placeholder-safe hook. The original project never claims, and the
        claim endpoint for drops is not confirmed, so this only logs a
        reminder unless the user opted in AND an endpoint is available.
        """
        claimable = [
            r for r in target.reward_lines
            if r.get("progress", 0) >= 1.0 and not r.get("claimed")
        ]
        if not claimable:
            return

        names = ", ".join(str(r.get("name")) for r in claimable)
        if not self.auto_claim:
            logger.success(t(
                "drops_reward_ready_manual",
                alias=self.alias, campaign=target.name, rewards=names,
            ))
            return

        logger.warning(t(
            "drops_claim_not_supported",
            alias=self.alias, campaign=target.name,
        ))

    # --------------------------------------------------------------- loop

    async def _sync_progress(self):
        """
        Pull real progress from Kick and finish any campaign that is now
        complete. If the campaign being watched is done, the session ends
        so the loop can move on to the next one.
        """
        ok = await self.refresh_campaigns()
        if not ok:
            logger.warning(t("drops_refresh_failed", alias=self.alias))
            return

        for target in self.targets.values():
            await self._maybe_claim(target)

        if self.session:
            current = self.targets.get(self.session.campaign_id)
            if current is None or current.done:
                name = current.name if current else self.session.campaign_id
                logger.success(t(
                    "drops_campaign_finished",
                    alias=self.alias, campaign=name,
                ))
                await self._end(t("drops_reason_finished"))
            elif current:
                logger.info(t(
                    "drops_progress_line",
                    alias=self.alias, campaign=current.name,
                    units=current.progress_units,
                    target=current.target_minutes,
                ))

    async def _verify_current(self) -> str:
        """
        Is the channel we are watching still live and still in the game?

        Returns one of:
          VERDICT_OK         keep watching as-is
          VERDICT_RECONNECT  same channel, but the streamer started a NEW
                             livestream (new id): the websocket has to be
                             re-opened against it. The channel itself is
                             fine, so it must NOT be excluded or marked
                             as tried.
          VERDICT_SWITCH     the channel is gone / changed game: move to
                             a different one.
        """
        if not self.session:
            return VERDICT_SWITCH
        target = self.targets.get(self.session.campaign_id)
        if target is None:
            return VERDICT_SWITCH

        state = await asyncio.to_thread(
            self.api.get_channel_state, self.session.slug
        )

        if state is None:
            # Can't tell. Do NOT count it as offline and do NOT abandon
            # a working session because of one blocked request.
            return VERDICT_OK

        if not state["is_live"]:
            self._offline_strikes += 1
            logger.debug(t(
                "drops_offline_strike",
                alias=self.alias, streamer=self.session.slug,
                strikes=self._offline_strikes,
                limit=self.offline_checks_to_switch,
            ))
            if self._offline_strikes < self.offline_checks_to_switch:
                return VERDICT_OK
            return VERDICT_SWITCH

        self._offline_strikes = 0

        # Live status and category come from the SAME request, so the
        # game is verified on every cycle at no extra cost.
        if (
            target.category_id
            and state["category_id"]
            and state["category_id"] != target.category_id
        ):
            logger.warning(t(
                "drops_category_changed",
                alias=self.alias, streamer=self.session.slug,
            ))
            return VERDICT_SWITCH

        # The stream restarted with a new id: the websocket must follow.
        if state["stream_id"] and state["stream_id"] != self.session.stream_id:
            logger.info(t(
                "drops_stream_restarted",
                alias=self.alias, streamer=self.session.slug,
            ))
            return VERDICT_RECONNECT

        return VERDICT_OK

    async def _choose_and_start(self, exclude: Optional[str] = None) -> bool:
        for target in self.pending_targets():
            if await self._begin(target, exclude=exclude):
                return True
        return False

    async def tick(self):
        """One decision cycle. Safe to call repeatedly."""
        async with self._lock:
            await self._sync_progress()

            pending = self.pending_targets()
            if not pending:
                if self.session:
                    await self._end(t("drops_reason_finished"))
                logger.info(t("drops_nothing_pending", alias=self.alias))
                return

            # A higher-priority campaign appeared/is available while we
            # are on a lower one: only switch if the current is done, to
            # avoid thrashing between campaigns mid-progress.
            if self.session:
                verdict = await self._verify_current()
                if verdict == VERDICT_OK:
                    return

                if verdict == VERDICT_RECONNECT:
                    # Same channel, new livestream id: reopen the
                    # websocket on it. Not "dead", so no exclusion.
                    slug = self.session.slug
                    target = self.targets.get(self.session.campaign_id)
                    await self._end(t("drops_reason_restarted"))
                    if target:
                        # `_begin` marks the channel as tried when it
                        # starts; a healthy channel being reconnected
                        # must be eligible again.
                        if slug in target.tried:
                            target.tried.remove(slug)
                        if await self._begin(target):
                            return
                    if await self._choose_and_start(exclude=slug):
                        return
                    logger.warning(
                        t("drops_no_live_channel", alias=self.alias)
                    )
                    return

                dead = self.session.slug
                await self._end(t("drops_reason_unavailable"))
                if await self._choose_and_start(exclude=dead):
                    return
                logger.warning(t("drops_no_live_channel", alias=self.alias))
                return

            if not await self._choose_and_start():
                logger.info(t("drops_no_live_channel", alias=self.alias))

    async def run(self):
        """Main loop. Cancel the task to stop."""
        self._running = True
        logger.info(t(
            "drops_started",
            alias=self.alias,
            interval=self.check_interval,
            claim=t("yes") if self.auto_claim else t("no"),
        ))

        try:
            while self._running:
                try:
                    await self.tick()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(t(
                        "drops_loop_error", alias=self.alias, error=str(e),
                    ))

                jitter = random.uniform(
                    self.check_interval * 0.85,
                    self.check_interval * 1.15,
                )
                await asyncio.sleep(jitter)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self):
        self._running = False
        await self._end(t("drops_reason_shutdown"))
        try:
            self.api.close()
        except Exception:
            pass

    # -------------------------------------------------------------- status

    def get_status(self) -> dict:
        return {
            "watching": self.watching_slug,
            "campaigns": {
                cid: {
                    "name": tg.name,
                    "game": tg.game,
                    "global": tg.is_global,
                    "done": tg.done,
                    "progress_units": tg.progress_units,
                    "target_minutes": tg.target_minutes,
                }
                for cid, tg in self.targets.items()
            },
        }
