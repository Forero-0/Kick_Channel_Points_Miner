# 🟢 Kick Channel Points Miner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> [🇷🇺 **Читать на русском языке**](README_RU.md) • [🇪🇸 **Leer en español**](README_es.md)

A powerful, asynchronous bot for automatically farming channel points on **Kick.com**. Features Telegram & Discord log notifications and Cloudflare protection bypass.

---

## ✨ Features

*   **👥 Multi-Account Support:** Farm points with up to 10+ accounts simultaneously, each with its own streamer list and limits.
*   **🎯 Priority System:** Streamers are prioritized by their position in the config. Higher-priority streamers automatically replace lower-priority ones when they go live.
*   **🔒 Concurrent Limits:** Set `max_concurrent` per account to control how many streamers are watched at once – prevents 403 rate-limiting.
*   **🌐 SOCKS5/HTTP Proxy:** Global or per-account proxy support to avoid IP blocks.
*   **🛡️ Cloudflare Bypass:** Built-in `curl_cffi` based session management with automatic retry on 403.
*   **📱 Telegram Notifications:** Push-only log notifications (startup, points gained, streamer status, errors, restarts) sent straight to your chat – just like the Discord webhook, it never listens for commands.
*   **🌐 Multi-language:** Support for English, Russian and Spanish.
*   **📉 Smart Logging:** Clean console output with optional Debug mode.
*   **♻️ Memory-Safe:** Sessions are reused and properly closed – no memory leaks during long runs.
*   **🎁 Drops Mining:** Watches Kick drop campaigns via WebSocket (no browser), syncs with Kick's real progress, and fails over between channels automatically.
*   **🔀 Drops First:** While an eligible drop campaign is active, one account watches exactly one eligible channel for drops. Points resume after the campaign is completed or no eligible channel remains.
*   **📣 Detailed Notifications:** Drops events can be enabled independently, and points notifications can optionally include the stream category.

---

## 🚀 Installation

1.  **Clone or Download** the repository:
    ```bash
    git clone https://github.com/Forero-0/Kick_Channel_Points_Miner.git
    cd Kick_Channel_Points_Miner
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure**: Rename `config.example.json` to `config.json` and fill it out (see below)

---

## ⚙️ Configuration (`config.json`)

### Multi-Account Format (Recommended)

```json
{
  "Language": "en",
  "Debug": false,

  "Telegram": {
    "enabled": false,
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_USER_ID",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "notify_restart": true,
    "notify_daily_reward": true,
    "drops_events": {
      "started": true,
      "stopped": true,
      "progress": true,
      "reward_ready": true,
      "claim_unavailable": true,
      "campaign_finished": true,
      "no_pending": true,
      "no_live_channel": true,
      "category_changed": true,
      "stream_restarted": true,
      "refresh_failed": true,
      "loop_error": true
    },
    "include_category_in_points": false,
    "min_points_gain": 10,
    "send_daily_reward_card": false
  },

  "Discord": {
    "enabled": false,
    "webhook_url": "https://discord.com/api/webhooks/XXXX/YYYY",
    "username": "KickMiner",
    "avatar_url": "",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "notify_restart": true,
    "notify_daily_reward": true,
    "min_points_gain": 10,
    "send_daily_reward_card": false,
    "color_success": 3461464,
    "color_info": 5793266,
    "color_warning": 16763904,
    "color_error": 15746887
  },

  "Proxy": {
    "enabled": false,
    "url": "socks5://user:password@host:port"
  },

  "Accounts": [
    {
      "alias": "Main Account",
      "token": "YOUR_KICK_TOKEN_1",
      "proxy": null,
      "streamers": ["streamer1", "streamer2", "streamer3"],
      "max_concurrent": 2
    },
    {
      "alias": "Second Account",
      "token": "YOUR_KICK_TOKEN_2",
      "proxy": "socks5://user:pass@proxy2:1080",
      "streamers": ["streamer2", "streamer3", "streamer4"],
      "max_concurrent": 1
    }
  ],

  "Check_interval": 120,
  "Reconnect_cooldown": 600,
  "Connection_stagger_min": 3,
  "Connection_stagger_max": 8
}
```

### Legacy Format (Still Supported)
The old single-account format is automatically converted:

```json
{
  "Language": "en",
  "Debug": false,
  "Telegram": { "enabled": false, "bot_token": "", "chat_id": "" },
  "Private": { "token": "YOUR_KICK_TOKEN" },
  "Streamers": ["stream1", "stream2", "stream3"],
  "Max_active_channels": 5
}
```

---

### Parameters description:

*   **`Language`**: Set to `"en"` or `"ru"`.
*   **`Debug`**: Set `"true"` for detailed logs, `"false"` for clean output.
*   **`Telegram`**:
    *   `bot_token`: Get this from @BotFather.
    *   `chat_id`: Your personal Telegram chat/user ID.
    *   `notify_points` / `notify_status_change` / `notify_errors` / `notify_startup` / `notify_restart` / `notify_daily_reward`: Toggle which event types get sent to Telegram. All `true` (send everything) by default.
    *   `min_points_gain`: Minimum points gain to trigger a `notify_points` notification.
    *   `send_daily_reward_card`: Whether the daily-reward card image is sent as an actual photo. `false` by default (text only); set to `true` if you also want the image.
    *   `drops_events`: Independently choose which drops events to send: `started`, `stopped`, `progress`, `reward_ready`, `claim_unavailable`, `campaign_finished`, `no_pending`, `no_live_channel`, `category_changed`, `stream_restarted`, `refresh_failed`, `loop_error`, `progress_unavailable`, `global_no_category` and `wrong_category`.
    *   `include_category_in_points`: Add the current stream category to each points-earned notification.
  *   **`Discord`**: Uses its own `drops_events` and `include_category_in_points` options independently from Telegram.
  *   **`Drops`**:
    *   `enabled`: Enable campaign discovery and mining for the account (global or per-account).
    *   `games` / `campaigns`: Restrict which campaigns are eligible. Empty lists accept all active campaigns.
    *   `auto_claim`: Reports claimable rewards; automatic claiming is not currently supported by the API integration.
    *   `check_interval`: Seconds between campaign/progress checks.
*   **`Proxy.enabled`**: Enable global proxy for all accounts.
    *   `Proxy.url`: Global proxy URL (`socks5://`, `http://`, `https://`).
*   **`Check_interval`**: Seconds between online status checks (default: `120`).
*   **`Reconnect_cooldown`**: Seconds before reconnection attempt (default: `600`).
*   **`Connection_stagger_min/max`**: Delay range (seconds) between connecting to streamers.
*   **`👥 Account Parameters`**:
    *   `alias`: Display name for the account.
    *   `token`: Kick authentication token (Bearer token).
    *   `proxy`: Per-account proxy (overrides global). Set `null` to use global
    *   `streamers`: Ordered list of streamer names. **Position = priority** (index 0 = highest)
    *   `max_concurrent`: 	Maximum number of streamers to watch simultaneously

---

## 🎯 How Priority Works
```
Config: ["streamer1", "streamer2", "streamer3", "streamer4"]
         Priority 0    Priority 1    Priority 2    Priority 3
         (Highest)                                  (Lowest)

max_concurrent: 2
```
Time | Event | Watching
| :--- | :--- | :--- |
T0 | streamer2 & streamer3 go live | `[streamer2, streamer3]`
T1 | streamer1 goes live (higher priority) | `[streamer1, streamer2]` ← streamer3 displaced!
T2	| streamer1 goes offline | `[streamer2, streamer3]` ← streamer3 returns
T3	| streamer4 goes live | `[streamer2, streamer3]` ← streamer4 waits (limit reached)

---

### 🔑 How to get your Kick Token

1.  Log in to **Kick.com** in your browser.
2.  Press `F12` to open Developer Tools.
3.  Go to the **Network** tab.
4.  Refresh the page (`F5`).
5.  Click on any request that appears (e.g., `auth.`).
6.  On the right panel, go to the **Headers** tab and scroll down to **Request Headers**.
7.  Find the `authorization` line.
8.  Copy the long string **after** the word `Bearer`. She looks like this `123456789|************************************`.
9. Paste this string into your `config.json` in the `"token"` field.

## 🎮 Usage

Run the miner:
```bash
python main.py
```

The bot will:

1. Load all accounts from config
2. Check which streamers are online
3. Connect to the top N (by priority) for each account
4. Dynamically rebalance when streamers go online/offline
5. Automatically restart on crashes

When drops are enabled and a pending campaign has an eligible live channel, drops have priority over channel points and only that channel is watched. The first drops decision is made before normal streamer selection, so an online followed streamer cannot take priority first. A followed streamer is reused for drops when it qualifies, which can mine both goals with one connection. Points earned on a drops-only channel are also reported with the same points message and marked as `Drops mining`. If the channel changes category or stops qualifying, the drops selector moves to another eligible channel. Once drops are complete, or no eligible channel is available, normal streamer priority resumes.

The drops integration is inspired by and credits [KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner). This project uses its own API/WebSocket integration and is not affiliated with that project.

### 📱 Telegram Notifications

The Telegram integration is **push-only**: it sends log-style notifications to `chat_id`, the same way the Discord webhook posts to a channel. It never listens for updates and has no commands to type.

**Configuration:**
```json
{
  "Telegram": {
    "enabled": true,
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_USER_ID",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "notify_restart": true,
    "notify_daily_reward": true,
    "min_points_gain": 10,
    "send_daily_reward_card": false
  }
}
```

| Parameter | Description |
| :--- | :--- |
| `bot_token` | Get this from @BotFather |
| `chat_id` | Your personal Telegram chat/user ID |
| `notify_points` | Send notifications when points are earned |
| `notify_status_change` | Notify when streamers go online/offline/displaced |
| `notify_errors` | Send error notifications |
| `notify_startup` | Send startup summary |
| `notify_restart` | Send a notification when the miner stops/restarts |
| `notify_daily_reward` | Send daily challenge reward notifications |
| `min_points_gain` | Minimum points gain to trigger a points notification |
| `send_daily_reward_card` | Send the daily-reward card as an actual photo. `false` (text only) by default |

All `notify_*` flags default to `true` — by default every event type is sent. Set any of them to `false` to silence just that event type, the same way Discord's flags work.

You'll get a message for:
*   🚀 Miner startup (accounts & streamers loaded) — if `notify_startup`
*   💰 Points gained per streamer — if `notify_points`
*   👁 Streamer status changes (started watching / displaced / online / offline) — if `notify_status_change`
*   ❌ Errors — if `notify_errors`
*   🎉 Daily challenge rewards claimed (if `ClaimDailyReward` is enabled and `notify_daily_reward` is true; includes the reward card image only if `send_daily_reward_card` is true)
*   🔄 Restarts/shutdowns — if `notify_restart` (sent synchronously right before the process exits, so it reliably arrives even when the bot is stopped with Ctrl+C)

---

### 🟣 Discord Webhook

Send real-time notifications to any Discord channel via webhooks – no bot required!

**Setup:**
1. In your Discord server, go to **Channel Settings → Integrations → Webhooks**
2. Click **New Webhook**, copy the URL
3. Paste into `config.json` → `Discord.webhook_url`

**Configuration:**
```json
{
  "Discord": {
    "enabled": true,
    "webhook_url": "https://discord.com/api/webhooks/XXXX/YYYY",
    "username": "KickMiner",
    "avatar_url": "",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "notify_restart": true,
    "notify_daily_reward": true,
    "min_points_gain": 10,
    "send_daily_reward_card": false,
    "color_success": 3461464,
    "color_info": 5793266,
    "color_warning": 16763904,
    "color_error": 15746887
  }
}
```

| Parameter | Description |
| :--- | :--- |
| `webhook_url` | Discord webhook URL |
| `username` | Bot display name in Discord |
| `avatar_url` | Custom avatar URL (optional) |
| `notify_points` | Send notifications when points are earned |
| `notify_status_change` | Notify when streamers go online/offline/displaced |
| `notify_errors` | Send error notifications |
| `notify_startup` | Send startup summary |
| `notify_restart` | Send a notification when the miner stops/restarts |
| `notify_daily_reward` | Send daily challenge reward notifications |
| `min_points_gain` | Minimum points gain to trigger notification |
| `send_daily_reward_card` | Send the daily-reward card as an actual image. `false` (text only) by default |
| `color_*` | 	Embed colors in decimal (use [color converter](https://www.mathsisfun.com/hexadecimal-decimal-colors.html)) |

Notifications include:

* 🚀 Startup summary with all accounts — if `notify_startup`
* 💰 Points earned (with streamer link) — if `notify_points`
* ▶️ Started watching / ⏹ Displaced by priority — if `notify_status_change`
* 🟢 Streamer online / 🔴 Streamer offline — if `notify_status_change`
* ❌ Error reports — if `notify_errors`
* 🎉 Daily challenge reward claimed — if `notify_daily_reward` (image attached only if `send_daily_reward_card` is true)
* 🔄 Restart/shutdown notifications — if `notify_restart`

---

### 🎯 Daily Reward Claim

Automatically checks and claims Kick's gamification daily challenge (watch-time reward + roulette prize), per account, and posts the result to Discord and/or Telegram (subject to each channel's own `notify_daily_reward` / `send_daily_reward_card` settings above).

**How it works — no fixed polling interval:**
1. When it starts (or right after claiming, or when a new day's challenge window begins), it asks Kick's API once how many watch-time minutes are still needed.
2. From then on it only counts time locally while the account is actually watching a stream. If nothing is being watched, the challenge can't progress on Kick's side either, so it doesn't bother calling the API at all during that dead time.
3. Once the accumulated watch time reaches what was missing, it checks again — if it's ready, it claims it automatically and logs/notifies the result.
4. Once claimed for the day, it stops touching the API entirely until the current challenge window ends, and only checks again after the next one starts — no wasted requests, no unnecessary polling.

**Configuration:**
```json
{
  "ClaimDailyReward": false
}
```

`ClaimDailyReward` is a single on/off switch — `true` enables the feature, `false` (default) disables it. Nothing else lives under this key anymore. Whether the claimed-reward event is posted to Discord/Telegram, and whether it includes the card photo, is controlled by that channel's own `notify_daily_reward` / `send_daily_reward_card` settings (see the Telegram and Discord sections above) — enabled by default for notifications, disabled by default for the photo.

When a reward is claimed, the notification shows:
* 🎉 Confirmation that the challenge was claimed
* 🏆 The reward's rarity, with its card image attached only if that channel's `send_daily_reward_card` is `true`
* 🎁 Or, if you already owned that card, how many extra watch-time minutes you got towards your next level instead

### 🎁 Drops Mining

Watches Kick **drop campaigns** for you.

**How it works:**
1. Asks Kick which campaigns are active and how far *you* actually are in each one.
2. Picks the first campaign that still needs time, skipping expired and already-claimed ones.
3. Finds a live channel for it and starts watching. **Kick's own progress is the source of truth** — the miner re-reads it every `check_interval` seconds and moves on as soon as a campaign is complete.
4. If the streamer goes offline, switches game, or restarts the stream, it switches to another channel of the campaign automatically.
5. Progress, rewards, channel changes, unavailable channels and errors can each be enabled or disabled independently under `Telegram.drops_events` and `Discord.drops_events`.

**Configuration** (everything is optional; drops are **off** unless `enabled` is `true`):
```json
{
  "Drops": {
    "enabled": true,
    "games": ["Rust"],
    "campaigns": [],
    "auto_claim": false,
    "check_interval": 300,
    "max_global_streamers": 24,
    "offline_checks_to_switch": 2
  }
}
```

| Parameter | Description |
| :--- | :--- |
| `enabled` | Master switch. `false` (default) leaves the miner exactly as it was. |
| `games` | Only mine campaigns of these games (name, partial match, case-insensitive). |
| `campaigns` | Only mine these campaigns (id or part of the name). **The order is the priority.** |
| `auto_claim` | Reserved. Automatic claiming is **not** available yet (see below). |
| `check_interval` | Seconds between progress/status checks (default `300`, minimum `60`). |
| `max_global_streamers` | For "global" campaigns, how many top live streamers of the game to consider (default `24`). |
| `offline_checks_to_switch` | Consecutive "offline" checks before abandoning a channel (default `2`). |

With **no** `games` and **no** `campaigns`, every active campaign is mined. You can also override the block **per account**:
```json
{ "alias": "Main", "token": "...", "streamers": ["a"], "drops": { "enabled": true, "games": ["Rust"] } }
```

**Two kinds of campaign** (detected automatically):
*   **Channel campaigns** — only the streamers Kick lists count.
*   **Global campaigns** — *any* streamer of the game counts; the miner picks live ones from the game's category.

---

## 🌐  Proxy Support

| Type | Format | Example |
| :--- | :--- | :--- |
| SOCKS5 | `socks5://user:pass@host:port` | `socks5://admin:123@proxy.com:1080` |
| SOCKS5 (no auth) | `socks5://host:port` | `socks5://proxy.com:1080` |
| HTTP | `http://user:pass@host:port` | `http://admin:123@proxy.com:8080` |
| HTTPS | `https://host:port` | `https://proxy.com:8080` |

Global proxy applies to all accounts. Per-account proxy overrides the global one.

---
## 📁 Project Structure

```
Kick_Channel_Points_Miner/
├── main.py                    # Entry point
├── account_manager.py         # Multi-account orchestrator with priorities
├── config.json                # Configuration
├── localization.py            # i18n loader
├── requirements.txt           # Dependencies
├── _websockets/
│   ├── ws_connect.py          # WebSocket client with proxy support
│   └── ws_token.py            # WS token acquisition
├── utils/
│   ├── kick_utility.py        # Channel/stream ID fetching
│   ├── get_points_amount.py   # Points balance checking
│   ├── drops_api.py           # Drops campaigns/progress API client
│   └── drops_miner.py         # Drops mining coordinator
├── discord_webhook.py         # Discord notifier
├── telegram.py                # Telegram notifier
└── lang/
    ├── en.lang                # English log messages
    └── ru.lang                # Russian log messages
```
---

## 🐳 Docker & Portainer Deployment

This is the recommended way to run the miner headlessly – great for home servers, NAS devices, or any machine running **Portainer**.

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/) installed (Desktop or Engine).
* A working `config.json` (copy `config.example.json` and edit it first).

---

### Option 1 – Docker CLI (quick)

```bash
# 1. Build the image (run from the project root)
docker build -t kick-channel-points-miner .

# 2. Start the container
docker run -d \
  --name kick-miner \
  --restart unless-stopped \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  kick-channel-points-miner
```

---

### Option 2 – Docker Compose

```bash
# Make sure config.json is in the same folder as docker-compose.yml
docker compose up -d
```

To stop: `docker compose down`
View logs: `docker compose logs -f`

---

### Option 3 – Portainer (GUI, beginner-friendly)

https://github.com/Baillora/Kick_Channel_Points_Miner/issues/4#issuecomment-3944659440

> **Tip:** Portainer will auto-restart the container on crash or server reboot thanks to `restart: unless-stopped`.

---

### Project Structure (with Docker files)

```
Kick_Channel_Points_Miner/
├── Dockerfile             # Container build instructions
├── docker-compose.yml     # Compose file for Docker / Portainer
├── .dockerignore          # Excludes config.json and dev files from image
├── config.json            # ← Created by you (bind-mounted, not baked in)
└── ...
```

> **Security note:** `config.json` is **never baked into the image**. It is always bind-mounted at runtime so your tokens stay on your host machine only.

---

## ⚠️ Disclaimer

This software is for educational purposes only. Use it at your own risk. The developer is not responsible for any bans or account restrictions on Kick.com.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.