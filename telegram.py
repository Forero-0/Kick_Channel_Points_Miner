import html
import threading
import time
from typing import List, Optional
from loguru import logger

try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
except ImportError:
    import requests as std_requests
    USE_CFFI = False

from localization import t, t_rarity


class TelegramBot:
    """
    Push-only Telegram notifier.

    Sends log-style notifications (startup, points gained, streamer
    status changes, errors, daily reward claims, restarts) to a single
    `chat_id`, the exact same way `DiscordWebhook` posts embeds to a
    Discord channel: a plain outbound HTTP call to the Telegram Bot API,
    fired from a background thread.

    It never listens for updates, never registers commands, and never
    polls Telegram for incoming messages.
    """

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, config: dict):
        tg_cfg = config.get("Telegram", {})

        self.enabled = tg_cfg.get("enabled", False)
        self.token = tg_cfg.get("bot_token", "")
        self.chat_id = tg_cfg.get("chat_id")

        # Which notification types to send (all on by default, same
        # semantics as DiscordWebhook's notify_* flags).
        self.notify_points = tg_cfg.get("notify_points", True)
        self.notify_status = tg_cfg.get("notify_status_change", True)
        self.notify_errors = tg_cfg.get("notify_errors", True)
        self.notify_startup = tg_cfg.get("notify_startup", True)
        self.notify_restart = tg_cfg.get("notify_restart", True)
        self.notify_daily_reward = tg_cfg.get("notify_daily_reward", True)
        default_drop_events = {
            "started": True,
            "stopped": True,
            "progress": True,
            "reward_ready": True,
            "claim_unavailable": True,
            "campaign_finished": True,
            "no_pending": True,
            "no_live_channel": True,
            "category_changed": True,
            "stream_restarted": True,
            "refresh_failed": True,
            "loop_error": True,
            "progress_unavailable": True,
            "global_no_category": True,
            "wrong_category": True,
        }
        self.drops_events = default_drop_events
        configured_drop_events = tg_cfg.get("drops_events", {})
        if isinstance(configured_drop_events, dict):
            self.drops_events.update(configured_drop_events)
        self.include_category = tg_cfg.get(
            "include_category_in_points", False
        )
        self.min_points_gain = tg_cfg.get("min_points_gain", 10)

        # Whether to send the daily-reward card as an actual photo.
        # Off by default so Telegram only sends text unless the user
        # opts in.
        self.send_daily_reward_card = tg_cfg.get(
            "send_daily_reward_card", False
        )

        # Rate limiting
        self._last_send_time = 0.0
        self._min_interval = 1.0
        self._lock = threading.Lock()

        if self.enabled and not self.token:
            logger.error(t("tg_token_not_found"))
            self.enabled = False

        if self.enabled and not self.chat_id:
            logger.error(t("tg_no_chat_id"))
            self.enabled = False

        if self.enabled:
            logger.success(t("tg_bot_initialized"))

    def _url(self, method: str) -> str:
        return self.API_URL.format(token=self.token, method=method)

    def _post(self, method: str, payload: dict) -> bool:
        if not self.enabled:
            return False

        with self._lock:
            now = time.time()
            elapsed = now - self._last_send_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

            try:
                url = self._url(method)
                if USE_CFFI:
                    resp = cffi_requests.post(url, json=payload, timeout=10)
                else:
                    resp = std_requests.post(url, json=payload, timeout=10)

                self._last_send_time = time.time()

                if resp.status_code == 200:
                    return True

                logger.error(t(
                    "tg_send_failed",
                    user_id=self.chat_id, error=f"HTTP {resp.status_code}",
                ))
                return False

            except Exception as e:
                logger.error(t(
                    "tg_send_failed", user_id=self.chat_id, error=str(e),
                ))
                return False

    def _send_in_thread(self, method: str, payload: dict):
        thread = threading.Thread(
            target=self._post, args=(method, payload), daemon=True,
        )
        thread.start()

    def _send_message(self, text: str, blocking: bool = False):
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if blocking:
            self._post("sendMessage", payload)
        else:
            self._send_in_thread("sendMessage", payload)

    def _send_photo(self, photo_url: str, caption: str = ""):
        self._send_in_thread("sendPhoto", {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        })

    # --- Notifications -----------------------------------------------

    def send_startup(self, accounts: List[dict]):
        """Notification: miner started"""
        if not self.enabled or not self.notify_startup:
            return

        lines = [t("tg_startup_title"), ""]
        for acc in accounts:
            alias = html.escape(acc.get("alias") or t("unknown_alias"))
            streamers = acc.get("streamer_order", [])
            limit = acc.get("max_concurrent", 0)
            proxy = "🔒" if acc.get("proxy") else "🌐"

            streamer_list = ", ".join(streamers[:5])
            if len(streamers) > 5:
                streamer_list += f" +{len(streamers) - 5}"

            lines.append(
                f"{proxy} <b>{alias}</b> [{limit}]: "
                f"<code>{html.escape(streamer_list)}</code>"
            )

        self._send_message("\n".join(lines))

    def send_points_update(
        self, account_alias, streamer, old_amount, new_amount,
        category=None,
        source=None,
    ):
        """Notification: points earned"""
        if not self.enabled or not self.notify_points:
            return

        gain = new_amount - old_amount
        if gain < self.min_points_gain:
            return

        prefix = f"[{html.escape(account_alias)}] " if account_alias else ""
        text = prefix + t(
            "tg_points_gained",
            streamer=f"<b>{html.escape(streamer)}</b>",
            gain=gain, total=new_amount,
        )
        if self.include_category and category:
            text += "\n" + t(
                "tg_points_category", category=html.escape(category)
            )
        if source == "drops":
            text += "\n" + t(
                "tg_points_source", source=t("tg_source_drops")
            )
        self._send_message(text)

    def send_streamer_online(
        self, account_alias, streamer, priority, action="started",
    ):
        """Notification: streamer went online / offline / started / displaced"""
        if not self.enabled or not self.notify_status:
            return

        icons = {
            "started": "👁", "displaced": "⏸",
            "online": "🟢", "offline": "⚫",
        }
        icon = icons.get(action, "📡")
        action_label = t(f"tg_action_{action}") if action in icons else action

        prefix = f"[{html.escape(account_alias)}] " if account_alias else ""
        text = prefix + t(
            "tg_streamer_status",
            icon=icon,
            streamer=f"<b>{html.escape(streamer)}</b>",
            action=action_label,
            priority=priority,
        )
        self._send_message(text)

    def send_drops_event(self, account_alias, event, message):
        """Notification: drops session or campaign event."""
        if not self.enabled or not self.drops_events.get(event, True):
            return

        self._send_message(
            f"[{html.escape(account_alias)}] "
            f"<b>{html.escape(t('tg_drops_title'))}</b>\n"
            f"{html.escape(message)}"
        )

    def send_error(self, account_alias, streamer, error):
        """Notification: error occurred"""
        if not self.enabled or not self.notify_errors:
            return

        safe = html.escape(str(error)[:300])
        prefix = f"[{html.escape(account_alias)}] " if account_alias else ""
        text = prefix + t(
            "tg_error_occurred",
            streamer=html.escape(streamer), error=safe,
        )
        self._send_message(text)

    def send_daily_reward_claimed(
        self,
        account_alias: str,
        rarity: Optional[str] = None,
        card_url: Optional[str] = None,
        watch_time_minutes: Optional[int] = None,
        already_owned: bool = False,
    ):
        """
        Notification: Kick daily gamification challenge claimed.
        Sends the reward card image (card_url) only if
        `send_daily_reward_card` is enabled in the Telegram config;
        otherwise sends text only.
        """
        if not self.enabled or not self.notify_daily_reward:
            return

        prefix = f"[{html.escape(account_alias)}] " if account_alias else ""

        if already_owned:
            text = prefix + t(
                "tg_daily_reward_consolation", minutes=watch_time_minutes,
            )
            self._send_message(text)
        else:
            caption = (
                prefix
                + t("tg_daily_reward_claimed")
                + "\n"
                + t("tg_daily_reward_rarity", rarity=t_rarity(rarity))
            )
            if card_url and self.send_daily_reward_card:
                self._send_photo(card_url, caption)
            else:
                self._send_message(caption)

    def send_restart(self, reason: str = None):
        """
        Notification: restart / shutdown.

        Sent synchronously (blocking) instead of via the usual
        fire-and-forget background thread. This method is always called
        right before the process exits (KeyboardInterrupt / SystemExit),
        so a background thread would frequently get killed mid-request
        before the HTTP call to Telegram completed, silently dropping
        the notification. Discord's send_restart has the same requirement
        and already sends synchronously for the same reason.
        """
        if not self.enabled or not self.notify_restart:
            return
        self._send_message(
            t("tg_restart_notification", reason=reason or t("restart_reason_manual")), blocking=True,
        )