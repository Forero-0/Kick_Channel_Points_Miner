import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from loguru import logger

from localization import t
from _websockets.ws_token import KickPoints
from _websockets.ws_connect import KickWebSocket
from utils.kick_utility import KickUtility
from utils.get_points_amount import PointsAmount
from utils.daily_challenge import DailyChallenge

if TYPE_CHECKING:
    from discord_webhook import DiscordWebhook
    from telegram import TelegramBot


@dataclass
class StreamerState:
    name: str
    priority: int

    is_online: bool = False
    is_watching: bool = False
    points: int = 0
    last_points_update: Optional[datetime] = None
    stream_id: Optional[int] = None
    channel_id: Optional[int] = None

    ws_client: Optional[KickWebSocket] = None
    ws_task: Optional[asyncio.Task] = None
    points_task: Optional[asyncio.Task] = None

    last_error: Optional[str] = None
    error_count: int = 0


@dataclass
class AccountState:
    alias: str
    token: str
    proxy: Optional[str]
    max_concurrent: int
    streamers: Dict[str, StreamerState] = field(default_factory=dict)
    streamer_order: List[str] = field(default_factory=list)

    @property
    def active_count(self) -> int:
        return sum(1 for s in self.streamers.values() if s.is_watching)

    @property
    def active_names(self) -> List[str]:
        return [s.name for s in self.streamers.values() if s.is_watching]


class AccountWorker:
    def __init__(
        self,
        account_cfg: dict,
        global_proxy: Optional[str] = None,
        check_interval: int = 120,
        reconnect_cooldown: int = 600,
        stagger_min: float = 3.0,
        stagger_max: float = 8.0,
        daily_challenge_enabled: bool = False,
    ):
        self.alias = account_cfg["alias"]
        self.token = account_cfg["token"]
        self.proxy = account_cfg.get("proxy") or global_proxy
        self.max_concurrent = account_cfg.get("max_concurrent", 2)
        self.check_interval = check_interval
        self.reconnect_cooldown = reconnect_cooldown
        self.stagger_min = stagger_min
        self.stagger_max = stagger_max
        self.daily_challenge_enabled = daily_challenge_enabled

        # Internal-only, not configurable: how often (seconds) the loop
        # wakes up to check "are we watching something right now" and add
        # to the accumulated watch time. This is NOT an API call, just a
        # local counter tick, so a short value is cheap and safe.
        self._DAILY_CHALLENGE_TICK_SECONDS = 30

        streamer_names: List[str] = account_cfg.get("streamers", [])

        self.state = AccountState(
            alias=self.alias,
            token=self.token,
            proxy=self.proxy,
            max_concurrent=self.max_concurrent,
            streamer_order=streamer_names,
        )
        for idx, name in enumerate(streamer_names):
            self.state.streamers[name] = StreamerState(
                name=name, priority=idx
            )

        self._utility_cache: Dict[str, KickUtility] = {}
        self._points_checker: Optional[PointsAmount] = None
        self._ws_token_getter: Optional[KickPoints] = None
        self._daily_challenge: Optional[DailyChallenge] = None
        self._daily_challenge_task: Optional[asyncio.Task] = None
        self._discord: Optional["DiscordWebhook"] = None
        self._tg_bot: Optional["TelegramBot"] = None

        self._rebalance_lock = asyncio.Lock()
        self._running = False

    def set_discord(self, discord: "DiscordWebhook"):
        self._discord = discord

    def set_tg_bot(self, tg_bot: "TelegramBot"):
        self._tg_bot = tg_bot

    def _get_utility(self, streamer: str) -> KickUtility:
        if streamer not in self._utility_cache:
            self._utility_cache[streamer] = KickUtility(
                streamer, proxy=self.proxy
            )
        return self._utility_cache[streamer]

    def _get_points_checker(self) -> PointsAmount:
        if self._points_checker is None:
            self._points_checker = PointsAmount(proxy=self.proxy)
        return self._points_checker

    def _get_ws_token_getter(self) -> KickPoints:
        if self._ws_token_getter is None:
            self._ws_token_getter = KickPoints(
                self.token, proxy=self.proxy
            )
        return self._ws_token_getter

    def _get_daily_challenge(self) -> DailyChallenge:
        if self._daily_challenge is None:
            self._daily_challenge = DailyChallenge(proxy=self.proxy)
        return self._daily_challenge

    async def start(self):
        self._running = True
        logger.info(t(
            "worker_starting",
            alias=self.alias,
            count=len(self.state.streamers),
            limit=self.max_concurrent,
            proxy=t("yes") if self.proxy else t("no"),
        ))

        if self.daily_challenge_enabled:
            self._daily_challenge_task = asyncio.create_task(
                self._daily_challenge_loop()
            )

        try:
            await self._check_all_online()
            await self._rebalance()

            while self._running:
                jitter = random.uniform(
                    self.check_interval * 0.8,
                    self.check_interval * 1.2,
                )
                await asyncio.sleep(jitter)
                await self._check_all_online()
                await self._rebalance()

        except asyncio.CancelledError:
            logger.info(t("worker_cancelled", alias=self.alias))
        except Exception as e:
            logger.error(t("worker_crashed", alias=self.alias, error=e))
        finally:
            await self.stop()

    async def _check_all_online(self):
        for name in self.state.streamer_order:
            if not self._running:
                break
            try:
                utility = self._get_utility(name)
                stream_id = utility.get_stream_id(self.token)

                st = self.state.streamers[name]
                was_online = st.is_online
                st.is_online = stream_id is not None
                st.stream_id = stream_id

                if not was_online and st.is_online:
                    logger.info(t(
                        "streamer_online",
                        alias=self.alias, streamer=name,
                        stream_id=stream_id,
                    ))
                    if self._discord:
                        self._discord.send_streamer_online(
                            self.alias, name,
                            st.priority, "online"
                        )
                    if self._tg_bot:
                        self._tg_bot.send_streamer_online(
                            self.alias, name,
                            st.priority, "online"
                        )

                elif was_online and not st.is_online:
                    logger.info(t(
                        "streamer_offline",
                        alias=self.alias, streamer=name,
                    ))
                    if self._discord:
                        self._discord.send_streamer_online(
                            self.alias, name,
                            st.priority, "offline"
                        )
                    if self._tg_bot:
                        self._tg_bot.send_streamer_online(
                            self.alias, name,
                            st.priority, "offline"
                        )

                elif not st.is_online:
                    logger.debug(t(
                        "streamer_offline_debug",
                        alias=self.alias, streamer=name,
                    ))

                await asyncio.sleep(random.uniform(1.0, 2.5))

            except Exception as e:
                logger.warning(t(
                    "error_checking_streamer",
                    alias=self.alias, streamer=name, error=e,
                ))

    async def _rebalance(self):
        async with self._rebalance_lock:
            online_by_priority = [
                name
                for name in self.state.streamer_order
                if self.state.streamers[name].is_online
            ]

            desired = set(
                online_by_priority[: self.max_concurrent]
            )
            current = {
                name
                for name, s in self.state.streamers.items()
                if s.is_watching
            }

            to_stop = current - desired
            for name in to_stop:
                is_offline = not self.state.streamers[name].is_online
                reason_key = "reason_offline" if is_offline else "reason_displaced"
                reason = t(reason_key)
                logger.info(t(
                    "streamer_stopped_reason",
                    alias=self.alias, streamer=name, reason=reason,
                ))
                await self._stop_streamer(name)

                if self._discord and reason_key == "reason_displaced":
                    self._discord.send_streamer_online(
                        self.alias, name,
                        self.state.streamers[name].priority,
                        "displaced"
                    )
                if self._tg_bot and reason_key == "reason_displaced":
                    self._tg_bot.send_streamer_online(
                        self.alias, name,
                        self.state.streamers[name].priority,
                        "displaced"
                    )

            to_start = desired - current
            for name in to_start:
                pri = self.state.streamers[name].priority
                logger.info(t(
                    "streamer_starting_priority",
                    alias=self.alias, streamer=name, priority=pri,
                ))
                await self._start_streamer(name)

                if self._discord:
                    self._discord.send_streamer_online(
                        self.alias, name, pri, "started"
                    )
                if self._tg_bot:
                    self._tg_bot.send_streamer_online(
                        self.alias, name, pri, "started"
                    )

                await asyncio.sleep(
                    random.uniform(
                        self.stagger_min, self.stagger_max
                    )
                )

            if desired:
                logger.info(t(
                    "worker_active_summary",
                    alias=self.alias,
                    streamers=sorted(desired),
                    count=len(desired),
                    limit=self.max_concurrent,
                ))

    async def _start_streamer(self, name: str):
        st = self.state.streamers[name]

        try:
            if not st.channel_id:
                utility = self._get_utility(name)
                st.channel_id = utility.get_channel_id(
                    self.token
                )
                if not st.channel_id:
                    raise RuntimeError(
                        t("failed_get_channel_id_for", streamer=name)
                    )

            ws_token_getter = self._get_ws_token_getter()
            ws_token = ws_token_getter.get_ws_token(name)
            if not ws_token:
                raise RuntimeError(
                    t("failed_get_ws_token_for", streamer=name)
                )

            async def on_disconnect():
                st.is_watching = False
                logger.warning(t(
                    "streamer_disconnected_final",
                    alias=self.alias, streamer=name,
                ))

            ws_client = KickWebSocket(
                data={
                    "token": ws_token,
                    "streamId": st.stream_id or 0,
                    "channelId": st.channel_id,
                },
                proxy=self.proxy,
                on_disconnect=on_disconnect,
            )

            st.ws_client = ws_client
            st.is_watching = True
            st.error_count = 0

            st.ws_task = asyncio.create_task(
                self._ws_wrapper(name, ws_client)
            )
            st.points_task = asyncio.create_task(
                self._points_loop(name)
            )

            try:
                pts = self._get_points_checker().get_amount(
                    name, self.token
                )
                if pts is not None:
                    st.points = pts
                    st.last_points_update = datetime.now()
            except Exception:
                pass

            logger.success(t(
                "now_watching", alias=self.alias, streamer=name,
            ))

        except Exception as e:
            logger.error(t(
                "error_starting_streamer",
                alias=self.alias, streamer=name, error=e,
            ))
            st.error_count += 1
            st.last_error = str(e)
            st.is_watching = False

            if self._discord:
                self._discord.send_error(
                    self.alias, name, str(e)
                )
            if self._tg_bot:
                self._tg_bot.send_error(
                    self.alias, name, str(e)
                )

    async def _stop_streamer(self, name: str):
        st = self.state.streamers[name]

        for task in (st.ws_task, st.points_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if st.ws_client:
            try:
                await st.ws_client.disconnect()
            except Exception:
                pass

        st.is_watching = False
        st.ws_client = None
        st.ws_task = None
        st.points_task = None
        logger.info(t("streamer_stopped", alias=self.alias, streamer=name))

    async def _ws_wrapper(
        self, name: str, ws_client: KickWebSocket
    ):
        try:
            await ws_client.connect()
        except Exception as e:
            logger.error(t(
                "ws_crashed", alias=self.alias, streamer=name, error=e,
            ))
        finally:
            self.state.streamers[name].is_watching = False

    async def _points_loop(self, name: str):
        st = self.state.streamers[name]
        checker = self._get_points_checker()

        while st.is_watching and self._running:
            try:
                await asyncio.sleep(random.uniform(120, 180))
                if not st.is_watching:
                    break

                amount = checker.get_amount(name, self.token)
                if amount is None:
                    continue

                old = st.points
                st.points = amount
                st.last_points_update = datetime.now()

                if amount > old:
                    gain = amount - old
                    logger.success(t(
                        "points_gain",
                        alias=self.alias, streamer=name,
                        gain=gain, amount=amount,
                    ))

                    if self._discord:
                        self._discord.send_points_update(
                            self.alias, name, old, amount
                        )
                    if self._tg_bot:
                        self._tg_bot.send_points_update(
                            self.alias, name, old, amount
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(t(
                    "points_error_for",
                    alias=self.alias, streamer=name, error=e,
                ))

    def _notify_daily_reward(self, outcome: dict):
        """
        Sends the Discord / Telegram notifications for a claimed daily
        reward. `outcome` is the "claimed": True branch returned by
        DailyChallenge.check_and_claim().

        Whether each channel actually sends anything (and whether it
        includes the reward card photo) is decided by that channel's own
        notifier (Telegram.notify_daily_reward / send_daily_reward_card,
        Discord.notify_daily_reward / send_daily_reward_card) — this only forwards
        the event to both.
        """
        result = outcome.get("result") or {}
        consolation = result.get("consolation")
        winner = result.get("winner", {}) or {}

        if consolation:
            already_owned = True
            rarity = None
            card_url = None
            watch_time_minutes = consolation.get("watch_time_minutes")
            logger.success(t(
                "daily_challenge_consolation",
                alias=self.alias, minutes=watch_time_minutes,
            ))
        else:
            already_owned = False
            rarity = winner.get("rarity", "unknown")
            card_url = winner.get("card_url")
            watch_time_minutes = None
            logger.success(t(
                "daily_challenge_claimed",
                alias=self.alias, rarity=rarity,
            ))

        if self._discord:
            self._discord.send_daily_reward_claimed(
                self.alias,
                rarity=rarity,
                card_url=card_url,
                watch_time_minutes=watch_time_minutes,
                already_owned=already_owned,
            )

        if self._tg_bot:
            self._tg_bot.send_daily_reward_claimed(
                self.alias,
                rarity=rarity,
                card_url=card_url,
                watch_time_minutes=watch_time_minutes,
                already_owned=already_owned,
            )

    async def _daily_challenge_loop(self):
        """
        Watches the Kick gamification daily challenge and claims it as
        soon as it's ready. Fully optional: controlled by
        ClaimDailyReward.enabled in config.json. Safe to disable/remove at
        any time without affecting the rest of the miner.

        This has no fixed "check every N seconds" polling. Instead:

          - On the first run (or right after claiming/after a new day's
            window starts), it calls the API once to learn exactly how
            many watch-time minutes are still missing
            (`remaining_minutes`).
          - From then on it only accumulates local watch time while this
            account is actually watching a stream (state.active_count >
            0). Dead air (nobody watching) doesn't count, since the
            challenge can't progress then either -> no point calling the
            API.
          - Once the accumulated watch time reaches `remaining_minutes`,
            it calls the API again to re-check/claim. If Kick says it's
            still not enough (our estimate was off), it just re-reads the
            new `remaining_minutes` and keeps accumulating.
          - Once claimed for the day, it stops touching the API entirely
            until the current challenge window ends (`window_ends_at`),
            same as before — no watch-time accounting needed while
            already claimed.

        A short internal tick (self._DAILY_CHALLENGE_TICK_SECONDS) is
        used only to sample "are we watching right now" locally; it never
        calls the Kick API by itself.
        """
        checker = self._get_daily_challenge()

        # None = "we don't know yet, need to ask the API before we can
        # accumulate anything meaningful".
        remaining_seconds: Optional[float] = None
        accumulated_seconds = 0.0
        sleep_until_next_window_check = False
        window_ends_at = None

        while self._running:
            try:
                if sleep_until_next_window_check:
                    # Already claimed today: just wait for the window to
                    # roll over, no watch-time accounting needed.
                    now = datetime.now(timezone.utc)

                    if window_ends_at is not None and window_ends_at <= now:
                        # The window we were waiting on has already ended -
                        # go re-check right away instead of waiting for
                        # another fallback window.
                        sleep_until_next_window_check = False
                        window_ends_at = None
                        remaining_seconds = None
                        accumulated_seconds = 0.0
                    else:
                        effective_end = window_ends_at
                        if effective_end is None:
                            # Kick didn't give us a usable window end at
                            # all - fall back to end of the current UTC
                            # day so we never spin-loop calling the API
                            # every tick.
                            effective_end = now.replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                            if effective_end <= now:
                                effective_end += timedelta(days=1)

                        seconds_left = (effective_end - now).total_seconds()
                        if seconds_left > 0:
                            await asyncio.sleep(min(seconds_left, 3600))
                            continue

                        # Fallback window also elapsed -> ask the API again.
                        sleep_until_next_window_check = False
                        window_ends_at = None
                        remaining_seconds = None
                        accumulated_seconds = 0.0

                is_watching = self.state.active_count > 0

                # Accumulate BEFORE evaluating the threshold. Previously the
                # threshold was checked first and the increment happened in
                # the "else" branch, so the tick that actually reached the
                # goal was never counted until the *next* loop iteration -
                # and if watching stopped in between (stream ended, account
                # switched channel, etc.) that final tick was lost forever,
                # so the estimate was never reached and claim() was never
                # called.
                if is_watching:
                    accumulated_seconds += self._DAILY_CHALLENGE_TICK_SECONDS
                    logger.debug(t(
                        "daily_challenge_progress",
                        alias=self.alias,
                        accumulated=int(accumulated_seconds),
                        remaining=(
                            int(remaining_seconds)
                            if remaining_seconds is not None else -1
                        ),
                    ))

                need_first_check = remaining_seconds is None
                reached_estimate = (
                    remaining_seconds is not None
                    and accumulated_seconds >= remaining_seconds
                )

                if need_first_check or reached_estimate:
                    outcome = checker.check_and_claim(self.token, self.alias)

                    if outcome.get("claimed"):
                        self._notify_daily_reward(outcome)
                        window_ends_at = None
                        sleep_until_next_window_check = True

                    elif outcome.get("already_claimed"):
                        window_ends_at = outcome.get("window_ends_at")
                        sleep_until_next_window_check = True

                    elif outcome.get("in_progress"):
                        remaining_minutes = outcome.get(
                            "remaining_minutes", 0
                        ) or 0
                        new_remaining_seconds = remaining_minutes * 60

                        # Kick reports remaining time in whole minutes, so it
                        # can still say e.g. "1 minute left" right after we
                        # already accumulated 59s. Blindly resetting
                        # accumulated_seconds to 0 here (old behaviour)
                        # threw away that progress and made us wait a full
                        # extra minute every single time we polled - in
                        # practice this could stall the claim indefinitely
                        # on accounts with short/interrupted watch sessions.
                        # Instead, only reset the counter if the API's
                        # figure implies MORE time is needed than we thought
                        # (e.g. after actually claiming yesterday and a new,
                        # bigger challenge started). Otherwise keep counting
                        # forward from where we are.
                        if (
                            remaining_seconds is None
                            or new_remaining_seconds > remaining_seconds
                        ):
                            remaining_seconds = new_remaining_seconds
                        else:
                            remaining_seconds = min(
                                remaining_seconds, new_remaining_seconds
                            )

                        logger.debug(t(
                            "daily_challenge_still_in_progress",
                            alias=self.alias,
                            remaining_minutes=remaining_minutes,
                            accumulated=int(accumulated_seconds),
                        ))

                        if remaining_seconds <= 0:
                            # Kick still reports "in progress" even though
                            # our math says the goal is met - avoid
                            # hammering the API every tick while it
                            # catches up; back off briefly instead.
                            await asyncio.sleep(60)

                    else:
                        # No challenge data at all (API/auth issue) -
                        # back off a bit before trying again so we don't
                        # spam a failing endpoint. Keep remaining_seconds/
                        # accumulated_seconds untouched so we don't lose
                        # progress just because of a transient API hiccup.
                        logger.warning(t(
                            "daily_challenge_check_failed_retry",
                            alias=self.alias,
                        ))
                        await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(t(
                    "daily_challenge_loop_error",
                    alias=self.alias, error=e,
                ))
                await asyncio.sleep(60)
                continue

            await asyncio.sleep(self._DAILY_CHALLENGE_TICK_SECONDS)

    async def stop(self):
        self._running = False

        if self._daily_challenge_task and not self._daily_challenge_task.done():
            self._daily_challenge_task.cancel()
            try:
                await self._daily_challenge_task
            except asyncio.CancelledError:
                pass

        for name in list(self.state.streamers):
            if self.state.streamers[name].is_watching:
                await self._stop_streamer(name)

        if self._points_checker:
            self._points_checker.close()
            self._points_checker = None

        if self._ws_token_getter:
            self._ws_token_getter.close()
            self._ws_token_getter = None

        if self._daily_challenge:
            self._daily_challenge.close()
            self._daily_challenge = None

        for u in self._utility_cache.values():
            u.close()
        self._utility_cache.clear()

        logger.info(t("worker_stopped", alias=self.alias))

    def get_status(self) -> dict:
        return {
            "alias": self.alias,
            "proxy": bool(self.proxy),
            "max_concurrent": self.max_concurrent,
            "active_count": self.state.active_count,
            "active_streamers": self.state.active_names,
            "streamer_order": self.state.streamer_order,
            "streamers": {
                name: {
                    "priority": s.priority,
                    "online": s.is_online,
                    "watching": s.is_watching,
                    "points": s.points,
                    "last_update": (
                        s.last_points_update.isoformat()
                        if s.last_points_update
                        else None
                    ),
                    "stream_id": s.stream_id,
                    "errors": s.error_count,
                }
                for name, s in self.state.streamers.items()
            },
        }


class AccountManager:
    def __init__(self, config: dict):
        self.workers: List[AccountWorker] = []
        self._tasks: List[asyncio.Task] = []
        self._discord: Optional["DiscordWebhook"] = None
        self._tg_bot: Optional["TelegramBot"] = None

        proxy_cfg = config.get("Proxy", {})
        global_proxy = (
            proxy_cfg.get("url")
            if proxy_cfg.get("enabled") else None
        )

        check_interval = config.get("Check_interval", 120)
        reconnect_cooldown = config.get(
            "Reconnect_cooldown", 600
        )
        stagger_min = config.get("Connection_stagger_min", 3)
        stagger_max = config.get("Connection_stagger_max", 8)

        # ClaimDailyReward is now a single on/off switch. Whether the
        # claimed-reward event gets posted to Discord/Telegram (and
        # whether it includes the card photo) is configured per-channel
        # under Discord.notify_daily_reward / Discord.send_daily_reward_card and
        # Telegram.notify_daily_reward / Telegram.send_daily_reward_card instead.
        daily_challenge_enabled = config.get("ClaimDailyReward", False)
        if not isinstance(daily_challenge_enabled, bool):
            daily_challenge_enabled = False

        # Backward compatibility with the old single-account config format
        accounts = config.get("Accounts", [])
        if not accounts:
            old_token = config.get(
                "Private", {}
            ).get("token", "")
            old_streamers = config.get("Streamers", [])
            old_max = config.get("Max_active_channels", 5)
            if old_token and old_streamers:
                accounts = [{
                    "alias": "Default",
                    "token": old_token,
                    "streamers": old_streamers,
                    "max_concurrent": old_max,
                }]
                logger.warning(t("legacy_config_warning"))

        for acc in accounts:
            self.workers.append(
                AccountWorker(
                    acc,
                    global_proxy=global_proxy,
                    check_interval=check_interval,
                    reconnect_cooldown=reconnect_cooldown,
                    stagger_min=stagger_min,
                    stagger_max=stagger_max,
                    daily_challenge_enabled=daily_challenge_enabled,
                )
            )

        logger.info(t(
            "accounts_loaded",
            count=len(self.workers),
            proxy=t("yes") if global_proxy else t("no"),
        ))

    def set_discord(self, discord: "DiscordWebhook"):
        """Attach a Discord webhook to every account worker."""
        self._discord = discord
        for worker in self.workers:
            worker.set_discord(discord)
        logger.info(t(
            "discord_connected_accounts", count=len(self.workers),
        ))

    def set_tg_bot(self, tg_bot: "TelegramBot"):
        """Attach the Telegram bot to every account worker."""
        self._tg_bot = tg_bot
        for worker in self.workers:
            worker.set_tg_bot(tg_bot)
        logger.info(t(
            "tg_bot_connected_accounts", count=len(self.workers),
        ))

    async def start_all(self):
        for i, worker in enumerate(self.workers):
            if i > 0:
                delay = random.uniform(5, 15)
                logger.info(t(
                    "delay_before_account",
                    delay=f"{delay:.0f}", alias=worker.alias,
                ))
                await asyncio.sleep(delay)

            task = asyncio.create_task(worker.start())
            self._tasks.append(task)

        await asyncio.gather(
            *self._tasks, return_exceptions=True
        )

    async def stop_all(self):
        for task in self._tasks:
            task.cancel()
        for w in self.workers:
            await w.stop()

    def get_all_status(self) -> List[dict]:
        return [w.get_status() for w in self.workers]

    def get_all_streamers_flat(self) -> List[str]:
        seen = set()
        result = []
        for w in self.workers:
            for s in w.state.streamer_order:
                if s not in seen:
                    seen.add(s)
                    result.append(s)
        return result