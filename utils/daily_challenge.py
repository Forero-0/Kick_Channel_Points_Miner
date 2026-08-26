from curl_cffi import requests
import json
from datetime import datetime, timezone
from loguru import logger
from localization import t


class DailyChallenge:
    """
    Handles Kick's daily gamification challenge (watch-time reward + roulette).
    One instance per account. Session is reused across calls.

    Endpoints used:
      GET  /api/v1/gamification/challenges              -> list current challenges
      POST /api/v1/gamification/challenges/{id}/claim    -> claim a completed challenge

    Challenge status values seen from the API so far:
      "in_progress" -> watch-time goal not reached yet, nothing to do.
      "claimed"     -> already claimed today, nothing to do until the next
                       challenge window starts.
      "claimable"   -> BEST GUESS for "goal reached, not yet claimed -> call
                       claim()".
    """

    READY_TO_CLAIM_STATUS = "claimable"

    BASE_URL = "https://web.kick.com/api/v1/gamification/challenges"

    def __init__(self, proxy: str = None):
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

    def _parse_response(self, response) -> dict | None:
        try:
            raw = response.content.decode("utf-8", errors="ignore")
            if not raw or raw.strip() in ("", "null", "None"):
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(t("daily_challenge_json_error", error=str(e)))
            return None

    def _safe_get(self, data, *keys):
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def get_challenges(self, token: str) -> list | None:
        """
        Returns the raw list of challenges (usually one: the daily watch-time
        challenge), or None on failure.
        """
        self.session.headers["Authorization"] = f"Bearer {token}"

        try:
            resp = self.session.get(self.BASE_URL, timeout=15)

            if resp.status_code == 401:
                logger.warning(t("daily_challenge_401"))
                return None

            if resp.status_code != 200:
                logger.error(t(
                    "daily_challenge_fetch_failed",
                    status=resp.status_code,
                ))
                return None

            data = self._parse_response(resp)
            if data is None:
                return None

            return self._safe_get(data, "data") or []

        except Exception as e:
            logger.error(t("daily_challenge_fetch_error", error=str(e)))
            return None

    def claim(self, token: str, challenge_id: str) -> dict | None:
        """
        Claims a challenge by id. Returns the parsed 'data' payload
        (winner card / roulette) on success, or None on failure.
        """
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Length"] = "0"

        try:
            resp = self.session.post(
                f"{self.BASE_URL}/{challenge_id}/claim",
                timeout=15,
            )

            if resp.status_code == 401:
                logger.warning(t("daily_challenge_401"))
                return None

            if resp.status_code != 200:
                logger.error(t(
                    "daily_challenge_claim_failed",
                    status=resp.status_code,
                ))
                return None

            data = self._parse_response(resp)
            if data is None:
                return None

            return self._safe_get(data, "data")

        except Exception as e:
            logger.error(t("daily_challenge_claim_error", error=str(e)))
            return None
        finally:
            self.session.headers.pop("Content-Length", None)

    @staticmethod
    def _parse_iso(value: str):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def check_and_claim(self, token: str, alias: str = "") -> dict:
        """
        High-level helper: fetches the current challenges, and if any is
        ready to claim (status == READY_TO_CLAIM_STATUS), claims it.

        Returns a dict describing what happened, always with a "claimed"
        bool key, so the caller (account_manager) can decide whether/how
        to notify Discord / Telegram, and how long to wait before asking
        the API again:

          {
            "claimed": False,
            "already_claimed": True/False,
            "window_ends_at": datetime | None,  # to know when the next
                                                  # challenge window starts
          }

        or, when still in progress:

          {
            "claimed": False,
            "already_claimed": False,
            "window_ends_at": datetime | None,
            "in_progress": True,
            "remaining_minutes": int,   # threshold - progress, so the
                                         # caller knows how much watch
                                         # time is still needed before
                                         # checking again
          }

        or, when something was actually claimed:

          {
            "claimed": True,
            "result": <raw "data" payload from the claim endpoint>,
          }
        """
        challenges = self.get_challenges(token)
        if not challenges:
            logger.debug(t("daily_challenge_none_found", alias=alias))
            return {"claimed": False, "already_claimed": False, "window_ends_at": None}

        for challenge in challenges:
            status = challenge.get("status")
            challenge_id = challenge.get("id")
            condition = challenge.get("condition") or {}
            progress = condition.get("progress", 0)
            threshold = condition.get("threshold", 0)
            window = challenge.get("window", {}) or {}
            window_ends_at = self._parse_iso(window.get("ends_at"))

            if status == "claimed":
                logger.debug(t(
                    "daily_challenge_already_claimed", alias=alias,
                ))
                return {
                    "claimed": False,
                    "already_claimed": True,
                    "window_ends_at": window_ends_at,
                }

            if status != self.READY_TO_CLAIM_STATUS:
                remaining = max(threshold - progress, 0)
                return {
                    "claimed": False,
                    "already_claimed": False,
                    "window_ends_at": window_ends_at,
                    "in_progress": True,
                    "remaining_minutes": remaining,
                }

            if not challenge_id:
                continue

            result = self.claim(token, challenge_id)
            if result is None:
                logger.error(t(
                    "daily_challenge_claim_no_result", alias=alias,
                ))
                continue

            return {"claimed": True, "result": result}

        return {"claimed": False, "already_claimed": False, "window_ends_at": None}