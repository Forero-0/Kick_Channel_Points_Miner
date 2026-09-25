# 🟢 Kick Channel Points Miner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> [🇷🇺 **Читать на русском языке**](README_RU.md) • [🇪🇸 **Leer en español**](README_es.md)

An asynchronous bot that automatically farms **channel points** and mines **drops** on **Kick.com**. It supports several accounts, priorities, proxies, and Telegram / Discord notifications.

> [!WARNING]
> **AI-assisted fork.** The changes made in this fork are implemented with the help of AI. Because of that, it may contain bugs, unexpected behavior or errors.

---

## 📑 Table of contents

- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration-configjson)
- [How to get your Kick token](#-how-to-get-your-kick-token)
- [Usage](#-usage)
- [How channel-points priority works](#-how-channel-points-priority-works)
- [Drops mining](#-drops-mining)
- [Telegram notifications](#-telegram-notifications)
- [Discord webhook](#-discord-webhook)
- [Daily reward claim](#-daily-reward-claim)
- [Proxy support](#-proxy-support)
- [Project structure](#-project-structure)
- [Docker & Portainer](#-docker--portainer)
- [Disclaimer](#-disclaimer)
- [License](#-license)

---

## ✨ Features

*   **👥 Multi-account:** Farm with several accounts at once, each with its own streamer list, limits and proxy.
*   **🎯 Priority system:** Streamers are prioritized by their position in the config. A higher-priority streamer that goes live replaces a lower-priority one.
*   **🎁 Drops mining:** Watches Kick drop campaigns through the WebSocket (no browser), uses Kick's real progress as the source of truth, claims rewards and switches channels automatically.
*   **🔀 Drops priority:** Campaigns and games are ranked by the order you write them. If something with a **higher priority** becomes available while you are on a lower one, the miner switches to it immediately.
*   **🔒 Concurrency limit:** `max_concurrent` per account controls how many streamers are watched at once and helps avoid 403 rate limits.
*   **🌐 SOCKS5 / HTTP proxy:** Global or per-account.
*   **🛡 Cloudflare bypass:** Session handling based on `curl_cffi` with retries on 403.
*   **📱 Telegram & Discord notifications:** Push-only notifications (they never listen for commands). Each event type can be enabled or disabled independently.
*   **🌍 Multi-language:** English, Russian and Spanish.
*   **📉 Clean logging:** Readable console output with an optional Debug mode.
*   **♻ Memory-safe:** Sessions are reused and closed properly, so long runs do not leak memory.

---

## 🚀 Installation

1.  **Clone or download** the repository:
    ```bash
    git clone https://github.com/Forero-0/Kick_Channel_Points_Miner.git
    cd Kick_Channel_Points_Miner
    ```

2.  **Install the dependencies** (Python 3.10 or newer):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure:** copy `config.example.json` to `config.json` and fill it in (see below).

---

## ⚙ Configuration (`config.json`)

### Multi-account format (recommended)

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
      "priority_switch": true,
      "reward_ready": true,
      "reward_claimed": true,
      "claim_unavailable": true,
      "claim_needs_link": true,
      "claim_failed": true,
      "campaign_finished": true,
      "no_pending": true,
      "no_live_channel": true,
      "category_changed": true,
      "stream_restarted": true,
      "refresh_failed": true,
      "loop_error": true,
      "progress_unavailable": true,
      "global_no_category": true,
      "wrong_category": true
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
    "drops_events": { "started": true, "stopped": true, "progress": true, "priority_switch": true },
    "include_category_in_points": false,
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

  "ClaimDailyReward": false,

  "Drops": {
    "enabled": false,
    "campaigns": [],
    "games": [],
    "auto_claim": true,
    "claim_retry_seconds": 1800,
    "check_interval": 300,
    "max_global_streamers": 24,
    "offline_checks_to_switch": 2,
    "points_grace_seconds": 600
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
      "max_concurrent": 1,
      "drops": { "enabled": true, "games": ["Rust"] }
    }
  ],

  "Check_interval": 120,
  "Reconnect_cooldown": 600,
  "Connection_stagger_min": 3,
  "Connection_stagger_max": 8
}
```

The full list of every `drops_events` key is in [`config.example.json`](config.example.json). Any key you leave out defaults to `true`.

### Legacy format (still supported)

The old single-account format is converted automatically:

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

### General parameters

| Parameter | Description |
| :--- | :--- |
| `Language` | `"en"`, `"ru"` or `"es"`. |
| `Debug` | `true` for detailed logs, `false` for clean output. |
| `Proxy.enabled` / `Proxy.url` | Global proxy for every account (`socks5://`, `http://`, `https://`). |
| `ClaimDailyReward` | `true` enables the daily reward claim (see [Daily reward claim](#-daily-reward-claim)). Default `false`. |
| `Check_interval` | Seconds between online-status checks (default `120`). |
| `Reconnect_cooldown` | Seconds before a reconnection attempt (default `600`). |
| `Connection_stagger_min` / `Connection_stagger_max` | Random delay range (seconds) between connections to streamers. |

### Account parameters

| Parameter | Description |
| :--- | :--- |
| `alias` | Display name of the account. |
| `token` | Kick authentication token (Bearer token). |
| `proxy` | Per-account proxy. Overrides the global one. `null` uses the global proxy. |
| `streamers` | Ordered list of streamers. **Position = priority** (index 0 is the highest). |
| `max_concurrent` | Maximum number of streamers watched at the same time (default `2`). |
| `drops` | Optional. Overrides the global `Drops` block for this account only. |

---

## 🔑 How to get your Kick token

1.  Log in to **Kick.com** in your browser.
2.  Press `F12` to open the developer tools.
3.  Go to the **Network** tab.
4.  Refresh the page (`F5`).
5.  Click any request that appears (for example `auth`).
6.  In the right panel open **Headers** and scroll to **Request Headers**.
7.  Find the `authorization` line.
8.  Copy the long string **after** the word `Bearer`. It looks like `123456789|************************************`.
9.  Paste it into the `"token"` field of your `config.json`.

---

## 🎮 Usage

```bash
python main.py
```

The miner will:

1. Load every account from the config.
2. Make the first drops decision (if drops are enabled).
3. Check which streamers are online.
4. Connect to the top N streamers (by priority) of each account.
5. Rebalance dynamically when streamers go online or offline.
6. Restart automatically after a crash.

---

## 🎯 How channel-points priority works

```
Config: ["streamer1", "streamer2", "streamer3", "streamer4"]
         Priority 0    Priority 1    Priority 2    Priority 3
         (highest)                                  (lowest)

max_concurrent: 2
```

| Time | Event | Watching |
| :--- | :--- | :--- |
| T0 | streamer2 and streamer3 go live | `[streamer2, streamer3]` |
| T1 | streamer1 goes live (higher priority) | `[streamer1, streamer2]` ← streamer3 displaced |
| T2 | streamer1 goes offline | `[streamer2, streamer3]` ← streamer3 returns |
| T3 | streamer4 goes live | `[streamer2, streamer3]` ← streamer4 waits (limit reached) |

---

## 🎁 Drops mining

Watches Kick **drop campaigns** for you. Drops are **off** unless `Drops.enabled` is `true`.

### How it works

1. Asks Kick which campaigns are active and how far *you* really are in each one.
2. Ranks the pending campaigns by priority (see below) and picks the best one that has a live channel. Expired and already-claimed campaigns are skipped.
3. Watches that channel. **Kick's own progress is the source of truth**: it is re-read every `check_interval` seconds.
4. If the streamer goes offline, changes game or restarts the stream, the miner moves to another channel of the campaign.
5. If a campaign with a **higher priority** becomes watchable, the miner switches to it immediately.
6. Rewards that reach 100 % are claimed automatically when `auto_claim` is `true`.
7. When everything is finished, or nobody eligible is live, channel points resume.

Kick only credits drops for one stream at a time, so each account watches **one** drops channel. While drops have work to do they take priority over channel points; a followed streamer is reused for drops when it qualifies.

### Priority (`campaigns` and `games`)

The priority is a single ladder built from your config. **Lower position = higher priority.**

1. Entries of `campaigns`, in the order you wrote them.
2. Entries of `games`, in the order you wrote them.
3. Anything else (only when no filters are set).

So a campaign listed in `campaigns` always beats a game listed in `games`, and inside each list the first entry wins.

```json
{
  "Drops": {
    "enabled": true,
    "campaigns": ["Special Event"],
    "games": ["Rust", "Valorant"]
  }
}
```

Resulting order: `Special Event` → `Rust` → `Valorant`.

#### What you can write in `campaigns` and `games`

Both are plain lists of text. Matching is **case-insensitive** (`"rust"` and `"Rust"` are the same) and checks for an **exact match first**; only if nothing matches exactly does it fall back to "the name contains this text".

| List | What each entry can be | Example entry | Matches |
| :--- | :--- | :--- | :--- |
| `campaigns` | The campaign's exact name, as Kick shows it | `"Rust Twitch Drops - Winter Chill"` | Only that exact campaign |
| `campaigns` | Part of the campaign's name (fallback, if no exact match exists) | `"Winter Chill"` | Any campaign whose name contains "Winter Chill" |
| `campaigns` | The campaign's internal id (rarely needed; visible in Kick's own drops page URL/API) | `"a1b2c3d4-..."` | Only that exact campaign |
| `games` | The game's exact name | `"Rust"` | Every active campaign for the game "Rust" |
| `games` | Part of the game's name (fallback) | `"Counter"` | Any game containing "Counter", e.g. "Counter-Strike 2" |

You do not need to guess the exact spelling: if you write something that does not match any campaign or game exactly, the miner still works as long as it is a *unique enough* substring — but an exact name is always safer and avoids accidental matches (see the "Rust" vs. "Trust Fall" example below).

#### Examples

**Only games, ranked by priority** — mine any campaign for these games, Rust first:
```json
{ "Drops": { "enabled": true, "games": ["Rust", "Valorant", "Counter-Strike 2"] } }
```

**Only specific campaigns, ranked by priority** — ignore everything else, even other campaigns of the same games:
```json
{ "Drops": { "enabled": true, "campaigns": ["Winter Chill Drops", "Summer Bash Drops"] } }
```

**Mixed: campaigns win over games** — `campaigns` always ranks above `games`, regardless of the order you type the two lists in the JSON file:
```json
{
  "Drops": {
    "enabled": true,
    "campaigns": ["Special Anniversary Event"],
    "games": ["Rust", "Valorant"]
  }
}
```
Priority here: `Special Anniversary Event` (1st) → `Rust` (2nd) → `Valorant` (3rd) → anything else is ignored.

**No filters at all** — mine every active campaign Kick offers, in the order Kick returns them (no particular priority):
```json
{ "Drops": { "enabled": true } }
```

**A single game, no priority needed** — a one-item list still works:
```json
{ "Drops": { "enabled": true, "games": ["Fortnite"] } }
```

Rules:

*   **Exact match first.** A name is matched exactly (campaign id, full campaign name, full game name) and only falls back to "contains" if there is no exact match. So `games: ["Rust"]` matches the game "Rust" exactly and will **not** accidentally capture an unrelated game called "Trust Fall" just because "rust" is a substring of "trust" — the exact-match check for "Rust" wins first.
*   **It switches up, never down.** A campaign that is more important than the current one triggers an immediate switch, as soon as one of its channels is live. A less important one never interrupts a working session.
*   **Several channels in one campaign** are equivalent: any of them earns the same progress, so the miner does not hop between them.
*   **A failed switch is safe.** If the better channel cannot be opened, the miner goes back to the channel it had and tries again on the next check.
*   With **no** `games` and **no** `campaigns`, every active campaign is mined, in the order Kick returns them.

### Drops parameters

| Parameter | Description |
| :--- | :--- |
| `enabled` | Master switch. `false` (default) leaves the miner untouched. |
| `campaigns` | Only mine these campaigns (id or name). **The order is the priority** and they rank above `games`. |
| `games` | Only mine campaigns of these games. **The order is the priority.** |
| `auto_claim` | `true` claims rewards automatically when they reach 100 %. `false` only reports them as ready. Default `false` in the code (`config.example.json` ships it as `true`). |
| `claim_retry_seconds` | Wait before retrying a failed claim, for example an unlinked game account (default `1800`, minimum `300`). |
| `check_interval` | Seconds between progress and status checks (default `300`, minimum `60`). |
| `max_global_streamers` | For global campaigns, how many top live streamers of the game are considered (default `24`). |
| `offline_checks_to_switch` | Consecutive "offline" checks before leaving a channel (default `2`). |
| `points_grace_seconds` | After drops lose their channel while a campaign is still pending, how long channel points stay paused (default `600`). |

You can override the whole block **per account**:

```json
{ "alias": "Main", "token": "...", "streamers": ["a"], "drops": { "enabled": true, "games": ["Rust"] } }
```

### Two kinds of campaign (detected automatically)

*   **Channel campaigns:** only the streamers Kick lists count.
*   **Global campaigns:** any streamer of the game counts; the miner picks live ones from the game's category.

### Claiming rewards

*   Each reward is claimed once. A failure is retried only after `claim_retry_seconds`.
*   If Kick asks you to **link your game account** (for example a publisher account), the miner tells you once and shows the link. It cannot link it for you.
*   With `auto_claim: false` you are told when a reward is ready and you claim it on kick.com.

### Drops events

Both `Telegram.drops_events` and `Discord.drops_events` accept these keys (independently, all `true` by default):

`started`, `stopped`, `progress`, `priority_switch`, `reward_ready`, `reward_claimed`, `claim_unavailable`, `claim_needs_link`, `claim_failed`, `campaign_finished`, `no_pending`, `no_live_channel`, `category_changed`, `stream_restarted`, `refresh_failed`, `loop_error`, `progress_unavailable`, `global_no_category`, `wrong_category`.

`include_category_in_points` adds the current stream category to every points notification. Points earned on a drops-only channel are reported with the same message and marked `Drops mining`.

### Credits

The drops integration is inspired by [KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner). This project has its own API / WebSocket implementation and is not affiliated with it.

---

## 📱 Telegram notifications

The integration is **push-only**: it sends log-style messages to `chat_id`, exactly like the Discord webhook. It never listens for updates and has no commands.

### Getting `bot_token` and `chat_id`

You need two values: the **bot token** (identifies your bot) and the **chat id** (tells the bot where to send messages, i.e. to you).

1.  **Create the bot and get `bot_token`:**
    1. Open Telegram and search for **@BotFather** (the official bot that creates other bots).
    2. Send `/newbot`.
    3. Choose a display name for your bot (anything, e.g. `My Kick Miner`).
    4. Choose a **username** for it — it must be unique and end in `bot` (e.g. `my_kick_miner_bot`).
    5. BotFather replies with a message containing your token, shaped like `123456789:ABCdefGhIJKlmNoPQRsTUvwxYZ`. That whole string is `bot_token`.
2.  **Start a chat with your bot and get `chat_id`:**
    1. Search for your bot by the username you just chose and open it.
    2. Press **Start** (or send any message, e.g. `hi`). This step is mandatory — a bot cannot message you first.
    3. In your browser, open `https://api.telegram.org/bot<TOKEN>/getUpdates`, replacing `<TOKEN>` with your `bot_token` (keep the `bot` prefix, e.g. `https://api.telegram.org/bot123456789:ABCdef.../getUpdates`).
    4. Look for `"chat":{"id":123456789,...}` in the JSON response. That number is your `chat_id`.
    5. If the response is `{"ok":true,"result":[]}` (empty), you skipped step 2 — send a message to the bot and reload the page.
3.  **Paste both values** into `config.json` → `Telegram.bot_token` and `Telegram.chat_id`, and set `Telegram.enabled` to `true`.

> **Group chats:** to notify a group instead of yourself, add the bot to the group and use the group's id (a negative number) as `chat_id`. The `getUpdates` method above works the same way once the bot has received a message in that group.

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
| `bot_token` | Get it from @BotFather. |
| `chat_id` | Your personal Telegram chat / user ID. |
| `notify_points` | Notify when points are earned. |
| `notify_status_change` | Notify when streamers go online / offline / are displaced. |
| `notify_errors` | Notify errors. |
| `notify_startup` | Send a startup summary. |
| `notify_restart` | Notify when the miner stops or restarts. |
| `notify_daily_reward` | Notify daily challenge rewards. |
| `drops_events` | Choose which drops events are sent (see [Drops events](#drops-events)). |
| `include_category_in_points` | Add the stream category to points notifications. |
| `min_points_gain` | Minimum gain that triggers a points notification. |
| `send_daily_reward_card` | Send the daily reward card as a real photo. `false` (text only) by default. |

Every `notify_*` flag defaults to `true`. Set one to `false` to silence just that event type.

You get a message for:

*   🚀 Miner startup: `notify_startup`
*   💰 Points gained per streamer: `notify_points`
*   👁 Streamer status changes: `notify_status_change`
*   🎁 Drops events: `drops_events`
*   ❌ Errors: `notify_errors`
*   🎉 Daily reward claimed (needs `ClaimDailyReward`): `notify_daily_reward`
*   🔄 Restarts / shutdowns: `notify_restart` (sent synchronously right before the process exits, so it arrives even with Ctrl+C)

---

## 🟣 Discord webhook

Real-time notifications in any Discord channel through a webhook. No bot needed.

**Setup:**

1. In your Discord server go to **Channel Settings → Integrations → Webhooks**.
2. Click **New Webhook** and copy the URL.
3. Paste it into `config.json` → `Discord.webhook_url`.

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
| `webhook_url` | Discord webhook URL. |
| `username` | Bot display name in Discord. |
| `avatar_url` | Custom avatar URL (optional). |
| `notify_points` | Notify when points are earned. |
| `notify_status_change` | Notify when streamers go online / offline / are displaced. |
| `notify_errors` | Notify errors. |
| `notify_startup` | Send a startup summary. |
| `notify_restart` | Notify when the miner stops or restarts. |
| `notify_daily_reward` | Notify daily challenge rewards. |
| `drops_events` | Choose which drops events are sent (see [Drops events](#drops-events)). |
| `include_category_in_points` | Add the stream category to points notifications. |
| `min_points_gain` | Minimum gain that triggers a points notification. |
| `send_daily_reward_card` | Attach the daily reward card as an image. `false` (text only) by default. |
| `color_*` | Embed colors in decimal (use a [color converter](https://www.mathsisfun.com/hexadecimal-decimal-colors.html)). |

Discord sends the same kinds of messages as Telegram (startup, points with a streamer link, watch start / displaced, online / offline, drops, errors, daily reward, restarts), each controlled by the flag above.

---

## 🎯 Daily reward claim

Automatically checks and claims Kick's gamification daily challenge (watch-time reward + roulette prize) per account, and posts the result to Discord and / or Telegram.

**How it works (no fixed polling interval):**

1. When it starts, right after claiming, or when a new day's window begins, it asks Kick once how many watch minutes are still missing.
2. From then on it only counts time locally while the account is actually watching a stream. With nothing to watch, the challenge cannot progress, so no request is made.
3. When the accumulated time reaches what was missing, it checks again and claims automatically.
4. Once claimed for the day it stops calling the API until the next window starts.

```json
{ "ClaimDailyReward": false }
```

`ClaimDailyReward` is a plain on / off switch (default `false`). Whether the event is posted, and whether it includes the card image, is controlled by each channel's own `notify_daily_reward` and `send_daily_reward_card` settings.

The notification shows the claim confirmation, the reward's rarity (with its card image only if `send_daily_reward_card` is `true`), or, if you already owned that card, the extra watch-time minutes you got instead.

---

## 🌐 Proxy support

| Type | Format | Example |
| :--- | :--- | :--- |
| SOCKS5 | `socks5://user:pass@host:port` | `socks5://admin:123@proxy.com:1080` |
| SOCKS5 (no auth) | `socks5://host:port` | `socks5://proxy.com:1080` |
| HTTP | `http://user:pass@host:port` | `http://admin:123@proxy.com:8080` |
| HTTPS | `https://host:port` | `https://proxy.com:8080` |

The global proxy applies to every account. A per-account proxy overrides it.

---

## 📁 Project structure

```
Kick_Channel_Points_Miner/
├── main.py                    # Entry point
├── account_manager.py         # Multi-account orchestrator with priorities
├── config.json                # Your configuration (you create it)
├── config.example.json        # Configuration template
├── localization.py            # i18n loader
├── discord_webhook.py         # Discord notifier
├── telegram.py                # Telegram notifier
├── memory_monitor.py          # Memory usage monitor
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container build
├── docker-compose.yml         # Compose file for Docker / Portainer
├── _websockets/
│   ├── ws_connect.py          # WebSocket client with proxy support
│   └── ws_token.py            # WebSocket token acquisition
├── utils/
│   ├── kick_utility.py        # Channel / stream ID fetching
│   ├── get_points_amount.py   # Points balance checking
│   ├── daily_challenge.py     # Daily reward claim
│   ├── drops_api.py           # Drops campaigns / progress / claim API client
│   └── drops_miner.py         # Drops coordinator (priority, switching, claiming)
└── lang/
    ├── en.lang                # English messages
    ├── es.lang                # Spanish messages
    └── ru.lang                # Russian messages
```

---

## 🐳 Docker & Portainer

The recommended way to run the miner headless, for example on a home server, a NAS or any machine with **Portainer**.

**Requirements:** [Docker](https://docs.docker.com/get-docker/) installed and a working `config.json` (copy `config.example.json` and edit it first).

### Option 1: Docker CLI

```bash
# 1. Build the image (from the project root)
docker build -t kick-channel-points-miner .

# 2. Start the container
docker run -d \
  --name kick-miner \
  --restart unless-stopped \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  kick-channel-points-miner
```

### Option 2: Docker Compose

```bash
# config.json must be in the same folder as docker-compose.yml
docker compose up -d
```

Stop: `docker compose down` · Logs: `docker compose logs -f`

### Option 3: Portainer (GUI)

Follow this guide: <https://github.com/Baillora/Kick_Channel_Points_Miner/issues/4#issuecomment-3944659440>

> **Tip:** the container restarts automatically after a crash or a server reboot thanks to `restart: unless-stopped`.

> **Security:** `config.json` is **never baked into the image**. It is always bind-mounted at runtime, so your tokens stay on your host.

---

## ⚠ Disclaimer

This software is for educational purposes only. Use it at your own risk. The developer is not responsible for bans or restrictions on your Kick.com account.

The changes in this fork are implemented with AI assistance and may contain errors (see the notice at the top).

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
