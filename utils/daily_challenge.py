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
        High-level helper: fetches ALL current challenges (Kick can run
        several at once, e.g. the permanent "Daily Reward" plus a seasonal
        event like "Trick or Treat"), claims every one that is ready and
        reports what is still pending.

        Every challenge is evaluated independently: one being claimed or
        in progress never hides the others.

        Returned dict (always has all keys):

          {
            "claimed": bool,            # at least one challenge claimed now
            "claims": [                 # one entry per successful claim
                {"id": str, "name": str, "result": <raw claim payload>},
            ],
            "claim_failed": bool,       # a claimable challenge failed to claim
            "already_claimed": bool,    # challenges exist and ALL are claimed
            "in_progress": bool,        # at least one is still short of goal
            "remaining_minutes": int,   # MIN remaining among in-progress ones
            "window_ends_at": datetime | None,
                # earliest window end among the relevant challenges: the
                # in-progress ones if any, otherwise all of them.
          }
        """
        outcome = {
            "claimed": False,
            "claims": [],
            "claim_failed": False,
            "already_claimed": False,
            "in_progress": False,
            "remaining_minutes": 0,
            "window_ends_at": None,
        }

        challenges = self.get_challenges(token)
        if not challenges:
            logger.debug(t("daily_challenge_none_found", alias=alias))
            return outcome

        all_windows = []
        pending_windows = []
        remaining_list = []

        for challenge in challenges:
            status = challenge.get("status")
            challenge_id = challenge.get("id")
            name = challenge.get("name") or ""
            condition = challenge.get("condition") or {}
            progress = condition.get("progress", 0) or 0
            threshold = condition.get("threshold", 0) or 0
            window = challenge.get("window", {}) or {}
            window_ends_at = self._parse_iso(window.get("ends_at"))

            if window_ends_at is not None:
                all_windows.append(window_ends_at)

            if status == "claimed":
                logger.debug(t(
                    "daily_challenge_already_claimed", alias=alias,
                ))
                continue

            if status == self.READY_TO_CLAIM_STATUS and challenge_id:
                result = self.claim(token, challenge_id)
                if result is None:
                    logger.error(t(
                        "daily_challenge_claim_no_result", alias=alias,
                    ))
                    outcome["claim_failed"] = True
                    continue
                outcome["claims"].append({
                    "id": challenge_id,
                    "name": name,
                    "result": result,
                })
                continue

            # Anything else (in_progress, unknown status): still pending.
            remaining_list.append(max(threshold - progress, 0))
            if window_ends_at is not None:
                pending_windows.append(window_ends_at)

        outcome["claimed"] = bool(outcome["claims"])

        if remaining_list:
            outcome["in_progress"] = True
            # A failed claim must be retried soon, not after the other
            # challenges' remaining watch time.
            outcome["remaining_minutes"] = (
                0 if outcome["claim_failed"] else min(remaining_list)
            )

        if (
            not remaining_list
            and not outcome["claim_failed"]
        ):
            outcome["already_claimed"] = not outcome["claimed"]

        relevant = pending_windows or all_windows
        outcome["window_ends_at"] = min(relevant) if relevant else None

        return outcome