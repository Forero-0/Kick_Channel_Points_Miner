import asyncio
import json
import sys
import os
import time
import traceback

from loguru import logger
from localization import load_language, t, DEFAULT_LANGUAGE

from account_manager import AccountManager
from discord_webhook import DiscordWebhook
from telegram import TelegramBot


def _read_configured_language(default=DEFAULT_LANGUAGE):
    """Best-effort read of config.json just for the Language key, so that
    even module-level log lines (before main() runs) use the right language."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("Language", default)
    except Exception:
        return default


# Load the language as early as possible so every log line, including ones
# emitted before main() runs, is consistent with the configured language
# instead of silently defaulting to English or mixing languages.
load_language(_read_configured_language())

# memory testing toggle
ENABLE_MEMORY_MONITOR = False

log_memory_usage = None
if ENABLE_MEMORY_MONITOR:
    try:
        from memory_monitor import log_memory_usage
    except ImportError:
        logger.warning(t("memory_monitor_not_found"))

telegram_bot = None
discord_hook = None
account_manager = None

async def main():
    global account_manager, telegram_bot, discord_hook

    # 1. Config
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.remove()
        log_level = "DEBUG" if config.get("Debug", False) else "INFO"
        logger.add(sys.stderr, level=log_level)

        load_language(config.get("Language", DEFAULT_LANGUAGE))

        logger.info(t("log_level_set", level=log_level))

    except Exception as e:
        logger.add(sys.stderr, level="INFO")
        logger.critical(t("config_load_error", error=e))
        return

    # 2. Account Manager
    account_manager = AccountManager(config)
    all_streamers = account_manager.get_all_streamers_flat()
    logger.info(t("total_unique_streamers", count=len(all_streamers)))

    # 3. Discord Webhook
    discord_hook = DiscordWebhook(config)
    if discord_hook.enabled:
        account_manager.set_discord(discord_hook)
        logger.info(t("discord_webhook_enabled"))

    # 4. Telegram
    telegram_bot = TelegramBot(config)
    if telegram_bot.enabled:
        account_manager.set_tg_bot(telegram_bot)

    # 5. Send startup notifications
    if discord_hook.enabled:
        discord_hook.send_startup(
            account_manager.get_all_status()
        )
    if telegram_bot.enabled:
        telegram_bot.send_startup(
            account_manager.get_all_status()
        )

    if log_memory_usage:
        asyncio.create_task(log_memory_usage(interval=60))
        logger.info(t("memory_monitor_started"))

    # 6. Start all accounts
    await account_manager.start_all()


if __name__ == "__main__":
    while True:
        try:
            logger.info(t("starting_miner"))
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info(t("stopped_by_user"))
            if discord_hook and discord_hook.enabled:
                discord_hook.send_restart("User stopped (Ctrl+C)")
            if telegram_bot and telegram_bot.enabled:
                telegram_bot.send_restart("User stopped (Ctrl+C)")
            sys.exit(0)
        except SystemExit:
            logger.info(t("restarting_system_exit"))
            if discord_hook and discord_hook.enabled:
                discord_hook.send_restart("SystemExit")
            if telegram_bot and telegram_bot.enabled:
                telegram_bot.send_restart("SystemExit")
        except Exception as e:
            logger.critical(t("critical_error_main", error=e))
            traceback.print_exc()
            if discord_hook and discord_hook.enabled:
                discord_hook.send_error("System", "main.py", str(e))
            if telegram_bot and telegram_bot.enabled:
                telegram_bot.send_error("System", "main.py", str(e))

        logger.info(t("restarting_in_seconds"))
        time.sleep(5)