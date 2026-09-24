# Приоритет дропсов

Если `Drops.enabled` включён и есть подходящая активная кампания, дропсы имеют приоритет над очками: аккаунт смотрит только один канал. Если канал есть в списке стримеров, соединение переиспользуется для одновременной добычи; при смене категории или потере подходящего статуса выбирается другой канал. После завершения кампаний или при отсутствии подходящего канала возвращается обычная добыча очков.

`drops_events` отдельно выбирает события дропсов в Discord и Telegram: `started`, `stopped`, `progress`, `reward_ready`, `claim_unavailable`, `campaign_finished`, `no_pending`, `no_live_channel`, `category_changed`, `stream_restarted`, `refresh_failed`, `loop_error`, `progress_unavailable`, `global_no_category` и `wrong_category`. `include_category_in_points` добавляет текущую категорию к каждому уведомлению о полученных очках. Очки, полученные на канале дропсов, также отправляются в том же формате с пометкой `Drops mining`.

Интеграция дропсов вдохновлена [KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner), которому здесь указаны кредиты. Реализация использует собственную интеграцию API/WebSocket и не связана с тем проектом.

# 🟢 Kick Channel Points Miner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> [🇬🇧 **Read in English**](README.md) • [🇪🇸 **Leer en español**](README_es.md)

Мощный асинхронный бот для автоматического фарма поинтов каналов на **Kick.com**. Поддержка мультиаккаунтов, система приоритетов, SOCKS5 прокси и лог-уведомления через Telegram и Discord.

---

## ✨ Возможности

*   **👥 Мультиаккаунт:** Фарм поинтов с 10+ аккаунтов одновременно, у каждого свой список стримеров и лимиты.
*   **🎯 Система приоритетов:** Стримеры приоритизируются по позиции в конфиге. При выходе в онлайн стримера с высоким приоритетом – он автоматически вытесняет стримера с низким.
*   **🔒 Лимиты одновременного просмотра:** Настройка `max_concurrent` на каждый аккаунт – предотвращает 403 ошибки.
*   **🌐 SOCKS5/HTTP прокси:** Глобальный или индивидуальный прокси для каждого аккаунта.
*   **🛡️ Обход Cloudflare:** Встроенная система на `curl_cffi` с авто-ретраем при 403.
*   **📱 Уведомления в Telegram:** Только отправка лог-уведомлений (запуск, начисленные поинты, статус стримеров, ошибки, перезапуски) прямо в ваш чат — так же, как работает вебхук Discord: бот никогда не слушает команды.
*   **🌐 Мультиязычность:** Английский и Русский.
*   **📉 Умное логирование:** Чистый вывод с опциональным Debug-режимом.
*   **♻️ Без утечек памяти:** Сессии переиспользуются и корректно закрываются.
*   **🎁 Майнинг дропсов:** Отслеживает кампании дропсов Kick через WebSocket (без браузера), синхронизируется с реальным прогрессом Kick и автоматически переключает каналы.

---

## 🚀 Установка

1.  **Клонируйте** репозиторий:
    ```bash
    git clone https://github.com/Forero-0/Kick_Channel_Points_Miner.git
    cd Kick_Channel_Points_Miner
    ```

2.  **Установите зависимости**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Настройте**: Переименуйте `config.example.json` в `config.json` и заполните (см. ниже).

---

## ⚙️ Конфигурация (`config.json`)

### Мультиаккаунт (рекомендуется)

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

### Старый формат (совместимость сохранена)
Старый формат для одной учетной записи автоматически преобразуется:

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

*   **`Language`**:  `"en"` или `"ru"`.
*   **`Debug`**: Установить `"true"` для дополнительных логов, `"false"` для чистого вывода.
*   **`Telegram`**:
    *   `bot_token`: Получите это от @BotFather.
    *   `chat_id`: Ваш личный chat/user ID в Telegram.
    *   `notify_points` / `notify_status_change` / `notify_errors` / `notify_startup` / `notify_restart` / `notify_daily_reward`: включают/выключают отправку каждого типа события в Telegram. По умолчанию все `true` (отправлять всё).
    *   `min_points_gain`: минимальный прирост поинтов для отправки уведомления `notify_points`.
    *   `send_daily_reward_card`: отправлять ли картинку карточки ежедневной награды как настоящее фото. По умолчанию `false` (только текст); поставьте `true`, если хотите и картинку.
*   **`Proxy.enabled`**: Включить глобальный прокси-сервер для всех учетных записей.
    *   `Proxy.url`: Глобальный URL-адрес прокси-сервера (`socks5://`, `http://`, `https://`).
*   **`Check_interval`**: Секунды между проверками состояния в режиме онлайн (по умолчанию: `120`).
*   **`Reconnect_cooldown`**: Секунды перед попыткой повторного подключения (по умолчанию: `600`).
*   **`Connection_stagger_min/max`**: Диапазон задержки (в секундах) между подключениями к стримерам.
*   **`👥 Параметры учетной записи`**:
    *   `alias`: Параметры учетной записи.
    *   `token`: токен проверки подлинности Kick (Bearer token).
    *   `proxy`: прокси-сервер для каждой учетной записи (переопределяет глобальный). Установите значение `null` чтобы использовать глобальный.
    *   `streamers`: упорядоченный список имен стримеров. **Позиция = приоритет** (индекс 0 = наивысший).
    *   `max_concurrent`: 	Максимальное количество стримеров для одновременного просмотра

---

## 🎯 Как работает приоритет
```
Конфиг: ["streamer1", "streamer2", "streamer3", "streamer4"]
         Приоритет 0   Приоритет 1   Приоритет 2   Приоритет 3
         (Высший)                                   (Низший)

max_concurrent: 2
```
Время | Событие | Просмотр
| :--- | :--- | :--- |
T0 | streamer2 и streamer3 в онлайне | `[streamer2, streamer3]`
T1 | streamer1 вышел в онлайн (выше приоритет) | `[streamer1, streamer2]` ← streamer3 вытеснен!
T2	| streamer1 ушёл в оффлайн | `[streamer2, streamer3]` ← streamer3 вернулся
T3	| streamer4 вышел в онлайн | `[streamer2, streamer3]` ← streamer4 ждёт (лимит)

---

### 🔑 Как получить токен Kick

1.  Зайдите на **Kick.com** и авторизуйтесь.
2.  Нажмите `F12`, чтобы открыть инструменты разработчика.
3.  Перейдите на вкладку **Network** (Сеть).
4.  Обновите страницу (`F5`).
5.  Нажмите на любой появившийся запрос (например, `auth`).
6.  В правой панели выберите вкладку **Headers** (Заголовки) и найдите раздел **Request Headers**.
7.  Найдите строку `Authorization`.
8.  Скопируйте длинную строку, которая идет **после** слова `Bearer`. Она выглядит вот так `123456789|*************************************`.
9. Вставьте эту строку в `config.json` в поле `"token"`.

---

## 🎮 Использование

Запуск майнера:
```bash
python main.py
```

Бот будет:

1. Загружать все аккаунты из конфига
2. Проверять, кто из стримеров онлайн
3. Подключаться к топ-N (по приоритету) для каждого аккаунта
4. Динамически перебалансировать при изменении статусов стримеров
5. Автоматически перезапускаться при сбоях

### 📱 Уведомления в Telegram

Интеграция с Telegram работает **только на отправку**: она посылает лог-уведомления на `chat_id`, точно так же, как вебхук Discord публикует сообщения в канал. Бот никогда не слушает обновления, и в нём нет команд для ввода.

**Конфигурация:**
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

| Параметр | Описание |
| :--- | :--- |
| `bot_token` | Получите это от @BotFather |
| `chat_id` | Ваш личный chat/user ID в Telegram |
| `notify_points` | Уведомлять при начислении поинтов |
| `notify_status_change` | Уведомлять об изменении статуса стримеров |
| `notify_errors` | Уведомлять об ошибках |
| `notify_startup` | Сводка при запуске |
| `notify_restart` | Уведомлять при остановке/перезапуске майнера |
| `notify_daily_reward` | Уведомлять о наградах ежедневного задания |
| `min_points_gain` | Минимальный прирост поинтов для уведомления |
| `send_daily_reward_card` | Отправлять карточку ежедневной награды как настоящее фото. По умолчанию `false` (только текст) |

Все флаги `notify_*` по умолчанию `true` — по умолчанию отправляется всё. Поставьте любой из них в `false`, чтобы отключить только этот тип события, точно так же, как работают флаги Discord.

Вы будете получать сообщения о:
*   🚀 Запуске майнера (загруженные аккаунты и стримеры) — если `notify_startup`
*   💰 Начисленных поинтах по каждому стримеру — если `notify_points`
*   👁 Изменении статуса стримера (начал просмотр / вытеснен / онлайн / офлайн) — если `notify_status_change`
*   ❌ Ошибках — если `notify_errors`
*   🎉 Полученных наградах ежедневного задания (если `ClaimDailyReward` включен и `notify_daily_reward` равен true; картинка карточки прикладывается только если `send_daily_reward_card` равен true)
*   🔄 Остановках/перезапусках — если `notify_restart` (отправляется синхронно прямо перед завершением процесса, поэтому надёжно доходит даже при остановке бота через Ctrl+C)

---

### 🟣 Discord Webhook

Уведомления в реальном времени в любой канал Discord через вебхуки – бот не нужен!

**Настройка:**
1. В Discord сервере: **Настройки канала → Интеграции → Вебхуки**
2. Нажмите **Новый вебхук**, скопируйте URL
3. Вставьте в `config.json` → `Discord.webhook_url`

**Конфигурация:**
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
| `webhook_url` | URL вебхука Discord |
| `username` | Имя бота в Discord |
| `avatar_url` | 	URL аватара (опционально) |
| `notify_points` | Уведомления о начислении поинтов |
| `notify_status_change` | Уведомления об изменении статуса стримеров |
| `notify_errors` | Уведомления об ошибках |
| `notify_startup` | Сводка при запуске |
| `notify_restart` | Уведомлять при остановке/перезапуске майнера |
| `notify_daily_reward` | Уведомлять о наградах ежедневного задания |
| `min_points_gain` | Минимальное начисление для уведомления |
| `send_daily_reward_card` | Отправлять карточку ежедневной награды как настоящую картинку. По умолчанию `false` (только текст) |
| `color_*` | 	Преобразуйте цвета в десятичную форму (используйте [color converter](https://www.mathsisfun.com/hexadecimal-decimal-colors.html)) |

Notifications include:

* 🚀 Сводка при запуске со всеми аккаунтами — если `notify_startup`
* 💰 Начисление поинтов (со ссылкой на стример) — если `notify_points`
* ▶️ Начало просмотра / ⏹ Вытеснение по приоритету — если `notify_status_change`
* 🟢 Стример онлайн / 🔴 Стример оффлайн — если `notify_status_change`
* ❌ Отчёты об ошибках — если `notify_errors`
* 🎉 Получена награда ежедневного задания — если `notify_daily_reward` (картинка прикладывается только если `send_daily_reward_card` равен true)
* 🔄 Уведомления о перезапуске/остановке — если `notify_restart`

---

### 🎯 Получение ежедневной награды

Автоматически проверяет и получает ежедневное игровое задание Kick (награда за время просмотра + приз рулетки) для каждого аккаунта, и публикует результат в Discord и/или Telegram (в зависимости от настроек `notify_daily_reward` / `send_daily_reward_card` каждого канала, см. выше).

**Как это работает — без фиксированного интервала опроса:**
1. При запуске (а также сразу после получения награды или в начале окна нового дня) один раз запрашивается API Kick, чтобы узнать, сколько минут просмотра ещё не хватает.
2. После этого время учитывается только локально и только пока аккаунт реально смотрит стрим. Если ничего не смотрится, задание всё равно не может продвигаться на стороне Kick, поэтому в это время API вообще не запрашивается.
3. Как только накопленное время просмотра достигает нужного значения, выполняется повторная проверка — если всё готово, награда получается автоматически, а результат логируется/отправляется в уведомлениях.
4. После получения награды за день API больше не запрашивается вплоть до окончания текущего окна задания, и проверка возобновляется только после начала следующего — без лишних и ненужных запросов.

**Конфигурация:**
```json
{
  "ClaimDailyReward": false
}
```

`ClaimDailyReward` — это простой переключатель вкл/выкл: `true` включает функцию, `false` (по умолчанию) выключает. Больше внутри этого ключа ничего нет. Публикуется ли событие полученной награды в Discord/Telegram и прикладывается ли к нему картинка карточки, определяется настройками самого канала (`notify_daily_reward` / `send_daily_reward_card`, см. разделы Telegram и Discord выше) — по умолчанию уведомления включены, а фото выключено.

При получении награды уведомление показывает:
* 🎉 Подтверждение получения задания
* 🏆 Редкость награды с прикреплённым изображением карточки, только если `send_daily_reward_card` этого канала равен `true`
* 🎁 Или, если карточка уже была у вас, сколько дополнительных минут просмотра вы получили для следующего уровня

### 🎁 Майнинг дропсов

Отслеживает **кампании дропсов** Kick за вас.

**Как это работает:**
1. Запрашивает у Kick активные кампании и ваш *реальный* прогресс в каждой.
2. Выбирает первую кампанию, где ещё нужно время, пропуская истёкшие и уже полученные.
3. Находит для неё канал в эфире и начинает просмотр. **Источник истины — прогресс Kick**: майнер перечитывает его каждые `check_interval` секунд и переходит дальше, как только кампания завершена.
4. Если стример ушёл в оффлайн, сменил игру или перезапустил стрим, майнер автоматически переключается на другой канал кампании.

**Конфигурация** (всё необязательно; дропсы **выключены**, пока `enabled` не равно `true`):
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

| Параметр | Описание |
| :--- | :--- |
| `enabled` | Главный переключатель. `false` (по умолчанию) оставляет майнер без изменений. |
| `games` | Майнить только кампании этих игр (название, частичное совпадение, без учёта регистра). |
| `campaigns` | Майнить только эти кампании (id или часть названия). **Порядок — это приоритет.** |
| `auto_claim` | Зарезервировано. Автоматическое получение **пока недоступно** (см. ниже). |
| `check_interval` | Секунды между проверками прогресса/статуса (по умолчанию `300`, минимум `60`). |
| `max_global_streamers` | Для «глобальных» кампаний — сколько топ-стримеров игры рассматривать (по умолчанию `24`). |
| `offline_checks_to_switch` | Сколько «оффлайн»-проверок подряд до отказа от канала (по умолчанию `2`). |

Без `games` **и** `campaigns` майнятся все активные кампании. Блок можно переопределить **для каждого аккаунта**:
```json
{ "alias": "Main", "token": "...", "streamers": ["a"], "drops": { "enabled": true, "games": ["Rust"] } }
```

**Два типа кампаний** (определяются автоматически):
*   **Кампании по каналам** — засчитываются только стримеры из списка Kick.
*   **Глобальные кампании** — засчитывается *любой* стример игры; майнер выбирает тех, кто в эфире, из категории игры.

---

## 🌐  Proxy Support

| Тип | Формат | Пример |
| :--- | :--- | :--- |
| SOCKS5 | `socks5://user:pass@host:port` | `socks5://admin:123@proxy.com:1080` |
| SOCKS5 (no auth) | `socks5://host:port` | `socks5://proxy.com:1080` |
| HTTP | `http://user:pass@host:port` | `http://admin:123@proxy.com:8080` |
| HTTPS | `https://host:port` | `https://proxy.com:8080` |

Глобальный прокси применяется ко всем аккаунтам. Прокси аккаунта переопределяет глобальный.

---
## 📁 Структура проекта

```
Kick_Channel_Points_Miner/
├── main.py                    # Точка входа
├── account_manager.py         # Мультиаккаунт-оркестратор с приоритетами
├── config.json                # Конфигурация
├── localization.py            # Загрузчик локализации
├── requirements.txt           # Зависимости
├── _websockets/
│   ├── ws_connect.py          # WebSocket клиент с поддержкой прокси
│   └── ws_token.py            # Получение WS-токена
├── utils/
│   ├── kick_utility.py        # Получение Channel/Stream ID
│   ├── get_points_amount.py   # Проверка баланса поинтов
│   ├── drops_api.py           # Клиент API кампаний/прогресса дропсов
│   └── drops_miner.py         # Координатор майнинга дропсов
├── discord_webhook.py         # Discord-нотификатор
├── telegram.py                # Telegram-нотификатор
└── lang/
    ├── en.lang                # Английские сообщения логов
    └── ru.lang                # Русские сообщения логов
```
---

## 🐳 Развертывание через Docker & Portainer

Это рекомендуемый способ запуска майнера в фоновом режиме (headless) – отлично подходит для домашних серверов, NAS-устройств или любых машин с установленным **Portainer**.

### Предварительные условия
* Установленный [Docker](https://docs.docker.com/get-docker/) (Desktop или Engine).
* Настроенный и рабочий `config.json` (скопируйте `config.example.json` и отредактируйте его перед запуском).

---

### Вариант 1 – Docker CLI (быстрый способ)

```bash
# 1. Соберите образ (запускать из корня проекта)
docker build -t kick-channel-points-miner .

# 2. Запустите контейнер
docker run -d \
  --name kick-miner \
  --restart unless-stopped \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  kick-channel-points-miner
```

---

### Вариант 2 – Docker Compose

```bash
# Убедитесь, что config.json находится в той же папке, что и docker-compose.yml
docker compose up -d
```

Остановить: `docker compose down`
Посмотреть логи: `docker compose logs -f`

---

### Вариант 3 – Portainer (GUI, beginner-friendly)

https://github.com/Baillora/Kick_Channel_Points_Miner/issues/4#issuecomment-3944659440

> **Совет:** Portainer автоматически перезапустит контейнер при сбое или перезагрузке сервера благодаря `restart: unless-stopped`.

---

### Структура проекта (с файлами Docker)

```
Kick_Channel_Points_Miner/
├── Dockerfile             # Инструкции по сборке контейнера
├── docker-compose.yml     # Compose файл для Docker / Portainer
├── .dockerignore          # Исключает config.json и dev-файлы из образа
├── config.json            # ← Создается вами (bind-mounted, не встраивается в образ)
└── ...
```

> **Примечание по безопасности:** `config.json` **никогда не встраивается в образ**. Он всегда монтируется во время выполнения, поэтому ваши токены остаются только на вашем хосте.


## ⚠️ Отказ от ответственности

Это программное обеспечение создано исключительно в образовательных целях. Используйте его на свой страх и риск. Разработчик не несет ответственности за возможные блокировки аккаунтов на Kick.com.

---

## 📜 Лицензия

Этот проект распространяется под лицензией MIT. Подробности смотрите в файле [LICENSE](LICENSE).