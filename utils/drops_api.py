from curl_cffi import requests
import json
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger
from localization import t


class DropsAPI:
    """
    Thin client for Kick's Drops endpoints. One instance per account,
    the session is reused across calls (same pattern as DailyChallenge).

    Endpoints used (all GET, none of them are documented by Kick, so the
    shapes below are inferred and every access is defensive):

      /api/v1/drops/campaigns   -> public, list of campaigns
      /api/v1/drops/progress    -> authenticated, per-user progress
      /api/v1/livestreams       -> live streamers of a category
      /api/v2/channels/{slug}   -> live status + current category

    Nothing in here downloads images or any other visual asset.
    """

    WEB_BASE = "https://web.kick.com/api/v1"
    CHANNEL_URL = "https://kick.com/api/v2/channels/{slug}"

    def __init__(self, token: str, proxy: str = None):
        self.token = token
        self.proxy = proxy

        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        self.session = requests.Session(
            impersonate="chrome120",
            proxies=proxies,
        )

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://kick.com",
            "Referer": "https://kick.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
        })

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _safe_get(data, *keys):
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def _get_json(self, url: str, authenticated: bool = False):
        """
        GET `url` and return the parsed JSON, or None on any failure.
        The Authorization header is only attached when `authenticated`
        is True, so public endpoints never carry the token.
        """
        headers = {}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            resp = self.session.get(url, headers=headers, timeout=15)

            if resp.status_code == 401:
                logger.warning(t("drops_401"))
                return None

            if resp.status_code == 403:
                logger.warning(t("drops_403", url=url))
                return None

            if resp.status_code != 200:
                logger.error(t(
                    "drops_http_error", status=resp.status_code, url=url,
                ))
                return None

            raw = resp.content.decode("utf-8", errors="ignore")
            if not raw or raw.strip() in ("", "null", "None"):
                return None
            return json.loads(raw)

        except Exception as e:
            logger.error(t("drops_request_error", url=url, error=str(e)))
            return None

    @staticmethod
    def parse_iso(value) -> Optional[datetime]:
        """ISO-8601 (with Z or offset) or unix timestamp -> aware UTC dt."""
        if value is None or value == "":
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @classmethod
    def is_expired(cls, campaign: dict) -> bool:
        """
        A campaign is expired when its `ends_at` is in the past.
        Unknown / unparseable end date => treated as NOT expired.

        The comparison is done in UTC on both sides. (The original
        project stripped the timezone and compared against local time,
        which shifts the expiry by the user's UTC offset.)
        """
        ends = cls.parse_iso(campaign.get("ends_at"))
        if ends is None:
            return False
        return ends <= datetime.now(timezone.utc)

    # ---------------------------------------------------------- campaigns

    def get_campaigns(self) -> Optional[List[dict]]:
        """
        Public list of drop campaigns, normalized. Returns None when the
        request itself failed (so the caller can tell "no campaigns"
        apart from "couldn't ask").

        Unlike the reference implementation, `category_id` is kept in the
        normalized dict, so a campaign never depends on the progress
        endpoint just to know which game it belongs to.
        """
        data = self._get_json(f"{self.WEB_BASE}/drops/campaigns")
        if data is None:
            return None

        raw_list = self._safe_get(data, "data")
        if raw_list is None and isinstance(data, list):
            raw_list = data
        if not isinstance(raw_list, list):
            return []

        campaigns = []
        for c in raw_list:
            if not isinstance(c, dict):
                continue

            category = c.get("category") or {}
            channels = []
            for ch in c.get("channels") or []:
                if not isinstance(ch, dict):
                    continue
                slug = (
                    ch.get("slug")
                    or self._safe_get(ch, "user", "username")
                )
                if not slug:
                    continue
                channels.append({
                    "slug": str(slug).lower(),
                    "username": (
                        self._safe_get(ch, "user", "username") or slug
                    ),
                })

            rewards = []
            for r in c.get("rewards") or []:
                if not isinstance(r, dict):
                    continue
                rewards.append({
                    "id": r.get("id"),
                    "name": r.get("name") or "?",
                    "required_units": r.get("required_units") or 0,
                })

            status = c.get("status") or "unknown"

            # Same inclusion rule as the reference project: keep a
            # campaign if it lists channels, or if it is active.
            if not channels and status != "active":
                continue

            campaigns.append({
                "id": c.get("id"),
                "name": c.get("name") or t("drops_unknown_campaign"),
                "game": category.get("name") or t("drops_unknown_game"),
                "category_id": category.get("id"),
                "status": status,
                "starts_at": c.get("starts_at"),
                "ends_at": c.get("ends_at"),
                "rewards": rewards,
                "channels": channels,
            })

        return campaigns

    # ----------------------------------------------------------- progress

    def get_progress(self) -> Optional[List[dict]]:
        """
        Authenticated, per-user progress, normalized. None on failure.

          {
            "id": <campaign id>, "status": "in progress" | "claimed" | ...,
            "progress_units": int,
            "category_id": int | None,
            "rewards": [ {"id", "name", "progress" (0..1), "claimed",
                          "required_units"} ]
          }
        """
        data = self._get_json(
            f"{self.WEB_BASE}/drops/progress", authenticated=True,
        )
        if data is None:
            return None

        raw_list = self._safe_get(data, "data")
        if raw_list is None and isinstance(data, list):
            raw_list = data
        if not isinstance(raw_list, list):
            return []

        out = []
        for p in raw_list:
            if not isinstance(p, dict):
                continue

            rewards = []
            for r in p.get("rewards") or []:
                if not isinstance(r, dict):
                    continue
                try:
                    prog = float(r.get("progress") or 0.0)
                except (TypeError, ValueError):
                    prog = 0.0
                rewards.append({
                    "id": r.get("id"),
                    "name": r.get("name") or "?",
                    "progress": max(0.0, min(prog, 1.0)),
                    "claimed": bool(r.get("claimed")),
                    "required_units": r.get("required_units") or 0,
                })

            out.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "status": p.get("status") or "unknown",
                "progress_units": p.get("progress_units") or 0,
                "category_id": self._safe_get(p, "category", "id"),
                "rewards": rewards,
            })

        return out

    # -------------------------------------------------------- live status

    def get_channel_state(self, slug: str) -> Optional[dict]:
        """
        Live status + current category of a channel, in ONE request.

        Returns {"is_live": bool, "category_id": int|None,
                 "stream_id": int|None, "channel_id": int|None}
        or None when the request failed / was blocked.

        Returning None (instead of guessing "live") is deliberate: the
        reference project failed towards "live" on a 403, which made its
        queue believe offline channels were streaming.
        """
        data = self._get_json(
            self.CHANNEL_URL.format(slug=slug), authenticated=True,
        )
        if not isinstance(data, dict):
            return None

        info = data.get("data") if isinstance(data.get("data"), dict) else data
        livestream = info.get("livestream")

        if not isinstance(livestream, dict) or not livestream.get("is_live"):
            return {
                "is_live": False, "category_id": None,
                "stream_id": None, "channel_id": info.get("id"),
            }

        categories = livestream.get("categories") or []
        category_id = None
        if categories and isinstance(categories[0], dict):
            category_id = categories[0].get("id")

        return {
            "is_live": True,
            "category_id": category_id,
            "stream_id": livestream.get("id"),
            "channel_id": info.get("id"),
        }

    def get_live_streamers(self, category_id, limit: int = 24) -> List[str]:
        """
        Slugs of the most-watched live streamers of a category, used for
        "global" campaigns (any streamer of the game counts).
        """
        url = (
            f"{self.WEB_BASE}/livestreams"
            f"?limit={int(limit)}&sort=viewer_count_desc"
            f"&category_id={category_id}"
        )
        data = self._get_json(url, authenticated=True)
        if data is None:
            return []

        # Tolerate both shapes: data.livestreams[] (nested) or data[] (flat)
        items = (
            self._safe_get(data, "data", "livestreams")
            or data.get("data")
            or []
        )
        if not isinstance(items, list):
            return []

        slugs = []
        for it in items:
            if not isinstance(it, dict):
                continue
            slug = (
                self._safe_get(it, "channel", "slug")
                or self._safe_get(it, "channel", "user", "username")
                or it.get("slug")
            )
            if slug:
                slugs.append(str(slug).lower())
        return slugs
