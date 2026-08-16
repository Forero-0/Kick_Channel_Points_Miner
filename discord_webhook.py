import json
import threading
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
except ImportError:
    import requests as std_requests
    USE_CFFI = False

from localization import t


class DiscordWebhook:

    def __init__(self, config: dict):
        discord_cfg = config.get("Discord", {})

        self.enabled = discord_cfg.get("enabled", False)
        self.webhook_url = discord_cfg.get("webhook_url", "")
        self.username = discord_cfg.get("username", "KickMiner")
        self.avatar_url = discord_cfg.get("avatar_url", "")

        # Which notification types to send
        self.notify_points = discord_cfg.get(
            "notify_points", True
        )
        self.notify_status = discord_cfg.get(
            "notify_status_change", True
        )
        self.notify_errors = discord_cfg.get(
            "notify_errors", True
        )
        self.notify_startup = discord_cfg.get(
            "notify_startup", True
        )
        self.min_points_gain = discord_cfg.get(
            "min_points_gain", 10
        )

        # Colors (decimal)
        self.color_success = discord_cfg.get(
            "color_success", 3461464  # #34D168
        )
        self.color_info = discord_cfg.get(
            "color_info", 5793266  # #5865F2
        )
        self.color_warning = discord_cfg.get(
            "color_warning", 16763904  # #FFA500
        )
        self.color_error = discord_cfg.get(
            "color_error", 15746887  # #F04747
        )

        # Rate limiting
        self._last_send_time = 0
        self._min_interval = 1.0
        self._lock = threading.Lock()

        if self.enabled and not self.webhook_url:
            logger.error(t("discord_webhook_url_missing"))
            self.enabled = False

        if self.enabled:
            logger.success(t("discord_webhook_initialized"))

    def _send_raw(self, payload: dict) -> bool:
        """Send the payload to the Discord webhook"""
        if not self.enabled:
            return False

        with self._lock:
            # Rate limit
            now = time.time()
            elapsed = now - self._last_send_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

            try:
                headers = {"Content-Type": "application/json"}
                data = json.dumps(payload)

                if USE_CFFI:
                    resp = cffi_requests.post(
                        self.webhook_url,
                        headers=headers,
                        data=data,
                        timeout=10,
                    )
                    status = resp.status_code
                else:
                    resp = std_requests.post(
                        self.webhook_url,
                        headers=headers,
                        data=data,
                        timeout=10,
                    )
                    status = resp.status_code

                self._last_send_time = time.time()

                if status == 204:
                    logger.debug(t("discord_message_sent"))
                    return True
                elif status == 429:
                    retry_after = 5
                    try:
                        body = resp.json()
                        retry_after = body.get(
                            "retry_after", 5
                        )
                    except Exception:
                        pass
                    logger.warning(t(
                        "discord_rate_limited",
                        retry_after=retry_after,
                    ))
                    time.sleep(retry_after)
                    return False
                else:
                    logger.error(t(
                        "discord_send_failed",
                        status=status,
                    ))
                    return False

            except Exception as e:
                logger.error(t(
                    "discord_send_error", error=str(e)
                ))
                return False

    def _send_in_thread(self, payload: dict):
        """Send in a background thread"""
        thread = threading.Thread(
            target=self._send_raw,
            args=(payload,),
            daemon=True,
        )
        thread.start()

    def _build_payload(
        self,
        embeds: List[dict],
        content: str = None,
    ) -> dict:
        payload = {}

        if self.username:
            payload["username"] = self.username
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds

        return payload

    def _embed(
        self,
        title: str,
        description: str = "",
        color: int = None,
        fields: List[dict] = None,
        footer: str = None,
        url: str = None,
        thumbnail_url: str = None,
    ) -> dict:
        embed: Dict[str, Any] = {"title": title}

        if description:
            embed["description"] = description
        if color is not None:
            embed["color"] = color
        if url:
            embed["url"] = url
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}

        embed["timestamp"] = datetime.utcnow().isoformat()

        return embed

    def _field(
        self, name: str, value: str, inline: bool = True
    ) -> dict:
        return {
            "name": name,
            "value": value,
            "inline": inline,
        }

    def send_startup(
        self,
        accounts: List[dict],
    ):
        """Notification: miner started"""
        if not self.enabled or not self.notify_startup:
            return

        fields = []
        for acc in accounts:
            alias = acc.get("alias", "Unknown")
            streamers = acc.get("streamer_order", [])
            limit = acc.get("max_concurrent", 0)
            proxy = t("discord_proxy") if acc.get("proxy") else t("discord_direct")

            streamer_list = ", ".join(
                streamers[:5]
            )
            if len(streamers) > 5:
                streamer_list += t(
                    "discord_more_streamers",
                    count=len(streamers) - 5,
                )

            fields.append(self._field(
                name=f"👤 {alias}",
                value=(
                    f"{proxy} · {t('discord_field_limit')}: {limit}\n"
                    f"`{streamer_list}`"
                ),
                inline=False,
            ))

        embed = self._embed(
            title=t("discord_startup_title"),
            description=t("discord_startup_desc", count=len(accounts)),
            color=self.color_success,
            fields=fields,
            footer=t("discord_footer"),
        )

        payload = self._build_payload([embed])
        self._send_in_thread(payload)

    def send_points_update(
        self,
        account_alias: str,
        streamer: str,
        old_amount: int,
        new_amount: int,
    ):
        """Notification: points earned"""
        if not self.enabled or not self.notify_points:
            return

        gain = new_amount - old_amount
        if gain < self.min_points_gain:
            return

        embed = self._embed(
            title=t("discord_points_title"),
            color=self.color_success,
            url=f"https://kick.com/{streamer}",
            fields=[
                self._field(t("discord_field_streamer"), f"[{streamer}](https://kick.com/{streamer})"),
                self._field(t("discord_field_gained"), f"+{gain:,}"),
                self._field(t("discord_field_total"), f"{new_amount:,}"),
                self._field(t("discord_field_account"), account_alias),
            ],
        )

        payload = self._build_payload([embed])
        self._send_in_thread(payload)

    def send_streamer_online(
        self,
        account_alias: str,
        streamer: str,
        priority: int,
        action: str = "started",
    ):
        """Notification: streamer went online / started watching"""
        if not self.enabled or not self.notify_status:
            return

        url = f"https://kick.com/{streamer}"

        if action == "started":
            title = t("discord_watching_title")
            color = self.color_success
            desc = t("discord_watching_desc", streamer=streamer, url=url)
        elif action == "displaced":
            title = t("discord_displaced_title")
            color = self.color_warning
            desc = t("discord_displaced_desc", streamer=streamer, url=url)
        elif action == "online":
            title = t("discord_online_title")
            color = self.color_info
            desc = t("discord_online_desc", streamer=streamer, url=url)
        elif action == "offline":
            title = t("discord_offline_title")
            color = self.color_warning
            desc = t("discord_offline_desc", streamer=streamer, url=url)
        else:
            title = f"📡 {action}"
            color = self.color_info
            desc = streamer

        embed = self._embed(
            title=title,
            description=desc,
            color=color,
            fields=[
                self._field(t("discord_field_account"), account_alias),
                self._field(t("discord_field_priority"), f"#{priority}"),
            ],
        )

        payload = self._build_payload([embed])
        self._send_in_thread(payload)

    def send_error(
        self,
        account_alias: str,
        streamer: str,
        error: str,
    ):
        """Notification: error occurred"""
        if not self.enabled or not self.notify_errors:
            return

        safe_error = str(error)[:500]

        embed = self._embed(
            title=t("discord_error_title"),
            description=f"```\n{safe_error}\n```",
            color=self.color_error,
            fields=[
                self._field(t("discord_field_account"), account_alias),
                self._field(t("discord_field_streamer"), streamer),
            ],
        )

        payload = self._build_payload([embed])
        self._send_in_thread(payload)

    def send_status_summary(
        self,
        accounts_status: List[dict],
    ):
        """Full status of all accounts (on demand)"""
        if not self.enabled:
            return

        embeds = []
        grand_total = 0

        for acc in accounts_status:
            alias = acc.get("alias", "Unknown")
            active = acc.get("active_count", 0)
            limit = acc.get("max_concurrent", 0)
            proxy = "🔒" if acc.get("proxy") else "🌐"  # icon-only, kept language-neutral
            streamers = acc.get("streamers", {})
            order = acc.get("streamer_order", list(streamers.keys()))

            acc_total = 0
            lines = []

            for name in order:
                info = streamers.get(name, {})
                pts = info.get("points", 0)
                acc_total += pts

                if info.get("watching"):
                    icon = "👁"
                elif info.get("online"):
                    icon = "🟢"
                else:
                    icon = "⚫"

                pri = info.get("priority", "?")
                err = (
                    f" ⚠️x{info['errors']}"
                    if info.get("errors", 0) > 0
                    else ""
                )

                lines.append(
                    f"{icon} #{pri} **{name}** — "
                    f"{pts:,} pts{err}"
                )

            grand_total += acc_total

            description = "\n".join(lines) if lines else t("discord_no_streamers")

            embed = self._embed(
                title=f"{proxy} {alias} [{active}/{limit}]",
                description=description,
                color=self.color_info,
                fields=[
                    self._field(
                        t("discord_field_subtotal"),
                        f"**{acc_total:,}** pts",
                    ),
                ],
            )
            embeds.append(embed)

        if len(embeds) > 10:
            embeds = embeds[:10]

        if embeds:
            embeds[-1]["footer"] = {
                "text": t("discord_grand_total", total=f"{grand_total:,}"),
            }

        payload = self._build_payload(embeds)
        self._send_in_thread(payload)

    def send_restart(self, reason: str = "Manual"):
        """Notification: restart"""
        if not self.enabled:
            return

        embed = self._embed(
            title=t("discord_restart_title"),
            description=t("discord_restart_desc", reason=reason),
            color=self.color_warning,
        )

        payload = self._build_payload([embed])
        self._send_raw(payload)

    def send_daily_reward_claimed(
        self,
        account_alias: str,
        rarity: str = None,
        card_url: str = None,
        watch_time_minutes: int = None,
        already_owned: bool = False,
    ):
        """
        Notification: Kick daily gamification challenge claimed.

        already_owned=True  -> Kick returned a "consolation" payload
                                (you already had this card, you got
                                {watch_time_minutes} min of level progress
                                instead).
        already_owned=False -> a new card was won; rarity/card_url describe
                                the reward and card_url is shown as an image.
        """
        if not self.enabled:
            return

        if already_owned:
            embed = self._embed(
                title=t("discord_daily_reward_title"),
                description=t(
                    "discord_daily_reward_consolation",
                    minutes=watch_time_minutes,
                ),
                color=self.color_info,
                fields=[
                    self._field(t("discord_field_account"), account_alias),
                ],
            )
        else:
            embed = self._embed(
                title=t("discord_daily_reward_title"),
                description=(
                    f"{t('discord_daily_reward_claimed')}\n"
                    f"{t('discord_daily_reward_rarity', rarity=rarity)}"
                ),
                color=self.color_success,
                fields=[
                    self._field(t("discord_field_account"), account_alias),
                ],
                thumbnail_url=None,
            )
            if card_url:
                embed["image"] = {"url": card_url}

        payload = self._build_payload([embed])
        self._send_in_thread(payload)

    def send_custom(
        self,
        title: str,
        description: str,
        color: int = None,
    ):
        """Custom message"""
        if not self.enabled:
            return

        embed = self._embed(
            title=title,
            description=description,
            color=color or self.color_info,
        )

        payload = self._build_payload([embed])
        self._send_in_thread(payload)