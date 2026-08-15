from curl_cffi import requests
import json
from loguru import logger
import time
import random
from localization import t


class PointsAmount:
    """
    One instance per account. The session is reused across calls.
    """

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
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://kick.com",
            "Referer": "https://kick.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
        })

        self._initialized = False

    def _ensure_session(self):
        if self._initialized:
            return
        try:
            resp = self.session.get("https://kick.com", timeout=15)
            if resp.status_code == 200:
                logger.debug(t("points_session_ok"))

            for name, value in {
                "showMatureContent": "true",
                "USER_LOCALE": "en",
            }.items():
                self.session.cookies.set(
                    name, value, domain="kick.com"
                )
            time.sleep(random.uniform(0.3, 1.0))
            self._initialized = True
        except Exception as e:
            logger.error(t("points_init_error", error=str(e)))

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _safe_get(self, data, *keys):
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def get_amount(self, username: str, token: str) -> int | None:
        self._ensure_session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Referer"] = (
            f"https://kick.com/{username}/"
        )

        try:
            resp = self.session.get(
                f"https://kick.com/api/v2/channels/"
                f"{username}/points",
                timeout=15,
            )

            if resp.status_code == 403:
                logger.warning(t("points_403_for", username=username))
                return None

            if resp.status_code == 404:
                return self._get_points_alt(username, token)

            if resp.status_code != 200:
                logger.error(t(
                    "points_api_error", username=username, status=resp.status_code
                ))
                return 0

            data = json.loads(
                resp.content.decode("utf-8", errors="ignore")
            )

            # Safe extraction
            points = self._safe_get(data, "data", "points")
            if points is not None:
                return points

            points = self._safe_get(data, "points")
            if points is not None:
                return points

            return 0

        except Exception as e:
            logger.error(t("points_generic_error", username=username, error=str(e)))
            return None

    def _get_points_alt(self, username: str, token: str) -> int:
        try:
            resp = self.session.get(
                f"https://kick.com/api/v2/channels/{username}",
                timeout=15,
            )
            if resp.status_code != 200:
                return 0

            data = json.loads(
                resp.content.decode("utf-8", errors="ignore")
            )

            points = self._safe_get(data, "data", "user", "points")
            if points is not None:
                return points

            points = self._safe_get(data, "user", "points")
            if points is not None:
                return points

            return 0

        except Exception:
            return 0