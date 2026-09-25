# 🟢 Kick Channel Points Miner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> [🇬🇧 **Read in English**](README.md) • [🇷🇺 **Читать на русском языке**](README_RU.md)

Un bot asíncrono que farmea automáticamente **puntos de canal** y mina **drops** en **Kick.com**. Soporta varias cuentas, prioridades, proxies y notificaciones por Telegram / Discord.

> [!WARNING]
> **Fork asistido por IA.** Los cambios de este fork se implementan con ayuda de IA. Por eso puede contener errores, comportamientos inesperados o fallos.

---

## 📑 Índice

- [Características](#-características)
- [Instalación](#-instalación)
- [Configuración](#-configuración-configjson)
- [Cómo obtener tu token de Kick](#-cómo-obtener-tu-token-de-kick)
- [Uso](#-uso)
- [Cómo funciona la prioridad de puntos](#-cómo-funciona-la-prioridad-de-puntos)
- [Minado de drops](#-minado-de-drops)
- [Notificaciones de Telegram](#-notificaciones-de-telegram)
- [Webhook de Discord](#-webhook-de-discord)
- [Reclamo de recompensa diaria](#-reclamo-de-recompensa-diaria)
- [Soporte de proxy](#-soporte-de-proxy)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Docker y Portainer](#-docker-y-portainer)
- [Aviso legal](#-aviso-legal)
- [Licencia](#-licencia)

---

## ✨ Características

*   **👥 Multi-cuenta:** Farmea con varias cuentas a la vez, cada una con su propia lista de streamers, límites y proxy.
*   **🎯 Sistema de prioridades:** Los streamers se priorizan por su posición en el config. Un streamer de mayor prioridad que sale en vivo reemplaza a uno de menor prioridad.
*   **🎁 Minado de drops:** Vigila las campañas de drops de Kick por WebSocket (sin navegador), usa el progreso real de Kick como fuente de verdad, reclama recompensas y cambia de canal automáticamente.
*   **🔀 Prioridad de drops:** Las campañas y los juegos se ordenan según el orden en que los escribas. Si aparece algo de **mayor prioridad** mientras estás en uno de menor prioridad, el miner cambia de inmediato.
*   **🔒 Límite de concurrencia:** `max_concurrent` por cuenta controla cuántos streamers se ven a la vez y ayuda a evitar límites 403.
*   **🌐 Proxy SOCKS5 / HTTP:** Global o por cuenta.
*   **🛡 Bypass de Cloudflare:** Gestión de sesiones basada en `curl_cffi` con reintentos ante 403.
*   **📱 Notificaciones de Telegram y Discord:** Solo envío (nunca escuchan comandos). Cada tipo de evento se activa o desactiva de forma independiente.
*   **🌍 Multilenguaje:** Inglés, ruso y español.
*   **📉 Registro limpio:** Salida de consola legible con modo Debug opcional.
*   **♻ Seguro en memoria:** Las sesiones se reutilizan y se cierran bien, sin fugas en ejecuciones largas.

---

## 🚀 Instalación

1.  **Clona o descarga** el repositorio:
    ```bash
    git clone https://github.com/Forero-0/Kick_Channel_Points_Miner.git
    cd Kick_Channel_Points_Miner
    ```

2.  **Instala las dependencias** (Python 3.10 o superior):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configura:** copia `config.example.json` a `config.json` y complétalo (ver más abajo).

---

## ⚙ Configuración (`config.json`)

### Formato multi-cuenta (recomendado)

```json
{
  "Language": "es",
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

La lista completa de claves de `drops_events` está en [`config.example.json`](config.example.json). Cualquier clave que omitas vale `true` por defecto.

### Formato legado (aún soportado)

El antiguo formato de una sola cuenta se convierte automáticamente:

```json
{
  "Language": "es",
  "Debug": false,
  "Telegram": { "enabled": false, "bot_token": "", "chat_id": "" },
  "Private": { "token": "YOUR_KICK_TOKEN" },
  "Streamers": ["stream1", "stream2", "stream3"],
  "Max_active_channels": 5
}
```

### Parámetros generales

| Parámetro | Descripción |
| :--- | :--- |
| `Language` | `"en"`, `"ru"` o `"es"`. |
| `Debug` | `true` para logs detallados, `false` para salida limpia. |
| `Proxy.enabled` / `Proxy.url` | Proxy global para todas las cuentas (`socks5://`, `http://`, `https://`). |
| `ClaimDailyReward` | `true` activa el reclamo de la recompensa diaria (ver [Reclamo de recompensa diaria](#-reclamo-de-recompensa-diaria)). Por defecto `false`. |
| `Check_interval` | Segundos entre comprobaciones de estado online (por defecto `120`). |
| `Reconnect_cooldown` | Segundos antes de reintentar una conexión (por defecto `600`). |
| `Connection_stagger_min` / `Connection_stagger_max` | Rango de retraso aleatorio (segundos) entre conexiones a streamers. |

### Parámetros de cuenta

| Parámetro | Descripción |
| :--- | :--- |
| `alias` | Nombre para mostrar de la cuenta. |
| `token` | Token de autenticación de Kick (Bearer token). |
| `proxy` | Proxy por cuenta. Sobrescribe el global. `null` usa el global. |
| `streamers` | Lista ordenada de streamers. **Posición = prioridad** (índice 0 es la más alta). |
| `max_concurrent` | Número máximo de streamers vistos a la vez (por defecto `2`). |
| `drops` | Opcional. Sobrescribe el bloque global `Drops` solo para esta cuenta. |

---

## 🔑 Cómo obtener tu token de Kick

1.  Inicia sesión en **Kick.com** en tu navegador.
2.  Pulsa `F12` para abrir las herramientas de desarrollador.
3.  Ve a la pestaña **Network**.
4.  Actualiza la página (`F5`).
5.  Haz clic en cualquier petición que aparezca (por ejemplo `auth`).
6.  En el panel derecho abre **Headers** y baja hasta **Request Headers**.
7.  Busca la línea `authorization`.
8.  Copia la cadena larga **después** de la palabra `Bearer`. Se ve así: `123456789|************************************`.
9.  Pégala en el campo `"token"` de tu `config.json`.

---

## 🎮 Uso

```bash
python main.py
```

El miner:

1. Carga todas las cuentas del config.
2. Toma la primera decisión de drops (si están activados).
3. Comprueba qué streamers están online.
4. Conecta a los N mejores (por prioridad) de cada cuenta.
5. Rebalancea dinámicamente cuando los streamers se conectan o desconectan.
6. Se reinicia automáticamente tras un fallo.

---

## 🎯 Cómo funciona la prioridad de puntos

```
Config: ["streamer1", "streamer2", "streamer3", "streamer4"]
         Prioridad 0   Prioridad 1  Prioridad 2  Prioridad 3
         (más alta)                              (más baja)

max_concurrent: 2
```

| Tiempo | Evento | Viendo |
| :--- | :--- | :--- |
| T0 | streamer2 y streamer3 salen en vivo | `[streamer2, streamer3]` |
| T1 | streamer1 sale en vivo (mayor prioridad) | `[streamer1, streamer2]` ← streamer3 desplazado |
| T2 | streamer1 se desconecta | `[streamer2, streamer3]` ← streamer3 vuelve |
| T3 | streamer4 sale en vivo | `[streamer2, streamer3]` ← streamer4 espera (límite alcanzado) |

---

## 🎁 Minado de drops

Vigila por ti las **campañas de drops** de Kick. Los drops están **apagados** salvo que `Drops.enabled` sea `true`.

### Cómo funciona

1. Pregunta a Kick qué campañas están activas y cuánto llevas *realmente* en cada una.
2. Ordena las campañas pendientes por prioridad (ver abajo) y elige la mejor que tenga un canal en vivo. Se saltan las expiradas y las ya reclamadas.
3. Vigila ese canal. **El progreso de Kick es la fuente de verdad**: se relee cada `check_interval` segundos.
4. Si el streamer se desconecta, cambia de juego o reinicia el stream, el miner pasa a otro canal de la campaña.
5. Si una campaña de **mayor prioridad** pasa a estar disponible, el miner cambia a ella de inmediato.
6. Las recompensas que llegan al 100 % se reclaman automáticamente cuando `auto_claim` es `true`.
7. Cuando todo termina, o no hay nadie elegible en vivo, se reanudan los puntos de canal.

Kick solo acredita drops de un stream a la vez, así que cada cuenta vigila **un** canal de drops. Mientras los drops tengan trabajo pendiente tienen prioridad sobre los puntos de canal; un streamer que ya sigues se reutiliza para drops si cumple los requisitos.

### Prioridad (`campaigns` y `games`)

La prioridad es una única escalera construida a partir de tu config. **Menor posición = mayor prioridad.**

1. Las entradas de `campaigns`, en el orden en que las escribiste.
2. Las entradas de `games`, en el orden en que las escribiste.
3. Cualquier otra cosa (solo cuando no hay filtros).

Así, una campaña listada en `campaigns` siempre gana a un juego listado en `games`, y dentro de cada lista gana la primera entrada.

```json
{
  "Drops": {
    "enabled": true,
    "campaigns": ["Special Event"],
    "games": ["Rust", "Valorant"]
  }
}
```

Orden resultante: `Special Event` → `Rust` → `Valorant`.

#### Qué puedes escribir en `campaigns` y `games`

Ambas son simples listas de texto. La comparación **no distingue mayúsculas/minúsculas** (`"rust"` y `"Rust"` son lo mismo) y primero busca **coincidencia exacta**; solo si nada coincide exactamente, cae en "el nombre contiene este texto".

| Lista | Qué puede ser cada entrada | Ejemplo de entrada | A qué le hace match |
| :--- | :--- | :--- | :--- |
| `campaigns` | El nombre exacto de la campaña, tal como lo muestra Kick | `"Rust Twitch Drops - Winter Chill"` | Solo esa campaña exacta |
| `campaigns` | Parte del nombre de la campaña (respaldo, si no hay coincidencia exacta) | `"Winter Chill"` | Cualquier campaña cuyo nombre contenga "Winter Chill" |
| `campaigns` | El id interno de la campaña (rara vez necesario; visible en la propia página/API de drops de Kick) | `"a1b2c3d4-..."` | Solo esa campaña exacta |
| `games` | El nombre exacto del juego | `"Rust"` | Toda campaña activa del juego "Rust" |
| `games` | Parte del nombre del juego (respaldo) | `"Counter"` | Cualquier juego que contenga "Counter", ej. "Counter-Strike 2" |

No necesitas adivinar la ortografía exacta: si escribes algo que no coincide exactamente con ninguna campaña o juego, el miner igual funciona mientras sea un substring lo bastante único — pero un nombre exacto siempre es más seguro y evita coincidencias accidentales (ver el ejemplo de "Rust" vs. "Trust Fall" más abajo).

#### Ejemplos

**Solo juegos, ordenados por prioridad** — mina cualquier campaña de estos juegos, Rust primero:
```json
{ "Drops": { "enabled": true, "games": ["Rust", "Valorant", "Counter-Strike 2"] } }
```

**Solo campañas específicas, ordenadas por prioridad** — ignora todo lo demás, incluso otras campañas de los mismos juegos:
```json
{ "Drops": { "enabled": true, "campaigns": ["Winter Chill Drops", "Summer Bash Drops"] } }
```

**Mezcla: las campañas ganan a los juegos** — `campaigns` siempre va por encima de `games`, sin importar el orden en que escribas las dos listas en el archivo JSON:
```json
{
  "Drops": {
    "enabled": true,
    "campaigns": ["Special Anniversary Event"],
    "games": ["Rust", "Valorant"]
  }
}
```
Prioridad aquí: `Special Anniversary Event` (1º) → `Rust` (2º) → `Valorant` (3º) → todo lo demás se ignora.

**Sin ningún filtro** — mina todas las campañas activas que ofrece Kick, en el orden que Kick las devuelve (sin prioridad particular):
```json
{ "Drops": { "enabled": true } }
```

**Un solo juego, sin necesidad de prioridad** — una lista de un elemento también funciona:
```json
{ "Drops": { "enabled": true, "games": ["Fortnite"] } }
```

Reglas:

*   **Primero coincidencia exacta.** Un nombre se compara de forma exacta (id de campaña, nombre completo de campaña, nombre completo de juego) y solo si no hay coincidencia exacta se usa "contiene". Así, `games: ["Rust"]` coincide exactamente con el juego "Rust" y **no** captura por accidente un juego sin relación llamado "Trust Fall" solo porque "rust" es un substring de "trust" — la comprobación exacta de "Rust" gana primero.
*   **Sube de prioridad, nunca baja.** Una campaña más importante que la actual provoca un cambio inmediato, en cuanto uno de sus canales esté en vivo. Una menos importante nunca interrumpe una sesión que funciona.
*   **Varios canales en una misma campaña** son equivalentes: cualquiera de ellos da el mismo progreso, así que el miner no salta entre ellos.
*   **Un cambio fallido es seguro.** Si el canal mejor no se puede abrir, el miner vuelve al canal que tenía y lo intenta de nuevo en la siguiente comprobación.
*   Con **ningún** `games` y **ninguna** `campaigns`, se minan todas las campañas activas, en el orden que devuelve Kick.

### Parámetros de drops

| Parámetro | Descripción |
| :--- | :--- |
| `enabled` | Interruptor general. `false` (por defecto) deja el miner intacto. |
| `campaigns` | Solo mina estas campañas (id o nombre). **El orden es la prioridad** y van por encima de `games`. |
| `games` | Solo mina campañas de estos juegos. **El orden es la prioridad.** |
| `auto_claim` | `true` reclama las recompensas automáticamente al llegar al 100 %. `false` solo avisa de que están listas. Por defecto `false` en el código (`config.example.json` lo trae como `true`). |
| `claim_retry_seconds` | Espera antes de reintentar un reclamo fallido, por ejemplo una cuenta de juego sin vincular (por defecto `1800`, mínimo `300`). |
| `check_interval` | Segundos entre comprobaciones de progreso y estado (por defecto `300`, mínimo `60`). |
| `max_global_streamers` | En campañas globales, cuántos streamers en vivo del juego se consideran (por defecto `24`). |
| `offline_checks_to_switch` | Comprobaciones "offline" seguidas antes de abandonar un canal (por defecto `2`). |
| `points_grace_seconds` | Cuando los drops pierden su canal y aún hay una campaña pendiente, cuánto tiempo siguen pausados los puntos de canal (por defecto `600`). |

Puedes sobrescribir todo el bloque **por cuenta**:

```json
{ "alias": "Main", "token": "...", "streamers": ["a"], "drops": { "enabled": true, "games": ["Rust"] } }
```

### Dos tipos de campaña (se detectan automáticamente)

*   **Campañas por canales:** solo cuentan los streamers que Kick lista.
*   **Campañas globales:** cuenta cualquier streamer del juego; el miner elige los que están en vivo en la categoría del juego.

### Reclamo de recompensas

*   Cada recompensa se reclama una sola vez. Un fallo se reintenta solo tras `claim_retry_seconds`.
*   Si Kick te pide **vincular tu cuenta del juego** (por ejemplo una cuenta del publisher), el miner te avisa una vez y muestra el enlace. No puede vincularla por ti.
*   Con `auto_claim: false` se te avisa cuando una recompensa está lista y la reclamas tú en kick.com.

### Eventos de drops

Tanto `Telegram.drops_events` como `Discord.drops_events` aceptan estas claves (de forma independiente, todas `true` por defecto):

`started`, `stopped`, `progress`, `priority_switch`, `reward_ready`, `reward_claimed`, `claim_unavailable`, `claim_needs_link`, `claim_failed`, `campaign_finished`, `no_pending`, `no_live_channel`, `category_changed`, `stream_restarted`, `refresh_failed`, `loop_error`, `progress_unavailable`, `global_no_category`, `wrong_category`.

`include_category_in_points` añade la categoría actual del stream a cada notificación de puntos. Los puntos obtenidos en un canal solo de drops se notifican con el mismo mensaje y se marcan como `Drops mining`.

### Créditos

La integración de drops está inspirada en [KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner). Este proyecto tiene su propia implementación de API / WebSocket y no está afiliado a él.

---

## 📱 Notificaciones de Telegram

La integración es **solo de envío**: manda mensajes tipo log a `chat_id`, igual que el webhook de Discord. Nunca escucha actualizaciones y no tiene comandos.

### Cómo obtener `bot_token` y `chat_id`

Necesitas dos valores: el **token del bot** (identifica a tu bot) y el **chat id** (le dice al bot a dónde enviarte los mensajes, es decir, a ti).

1.  **Crea el bot y obtén `bot_token`:**
    1. Abre Telegram y busca **@BotFather** (el bot oficial que crea otros bots).
    2. Envíale `/newbot`.
    3. Elige un nombre para mostrar de tu bot (lo que quieras, por ejemplo `My Kick Miner`).
    4. Elige un **username** para él — debe ser único y terminar en `bot` (por ejemplo `my_kick_miner_bot`).
    5. BotFather te responde con un mensaje que contiene tu token, con esta forma: `123456789:ABCdefGhIJKlmNoPQRsTUvwxYZ`. Esa cadena completa es tu `bot_token`.
2.  **Inicia un chat con tu bot y obtén `chat_id`:**
    1. Busca tu bot por el username que elegiste y ábrelo.
    2. Pulsa **Start** (o envía cualquier mensaje, por ejemplo `hola`). Este paso es obligatorio — un bot no puede escribirte primero.
    3. En tu navegador, abre `https://api.telegram.org/bot<TOKEN>/getUpdates`, reemplazando `<TOKEN>` por tu `bot_token` (conserva el prefijo `bot`, por ejemplo `https://api.telegram.org/bot123456789:ABCdef.../getUpdates`).
    4. Busca `"chat":{"id":123456789,...}` en la respuesta JSON. Ese número es tu `chat_id`.
    5. Si la respuesta es `{"ok":true,"result":[]}` (vacía), te saltaste el paso 2 — envía un mensaje al bot y recarga la página.
3.  **Pega ambos valores** en `config.json` → `Telegram.bot_token` y `Telegram.chat_id`, y pon `Telegram.enabled` en `true`.

> **Chats de grupo:** para notificar a un grupo en vez de a ti mismo, añade el bot al grupo y usa el id del grupo (un número negativo) como `chat_id`. El método `getUpdates` de arriba funciona igual una vez que el bot haya recibido un mensaje en ese grupo.

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

| Parámetro | Descripción |
| :--- | :--- |
| `bot_token` | Consíguelo con @BotFather. |
| `chat_id` | Tu ID personal de chat / usuario de Telegram. |
| `notify_points` | Notificar cuando se ganen puntos. |
| `notify_status_change` | Notificar cuando los streamers se conectan / desconectan / son desplazados. |
| `notify_errors` | Notificar errores. |
| `notify_startup` | Enviar un resumen al iniciar. |
| `notify_restart` | Notificar cuando el miner se detiene o reinicia. |
| `notify_daily_reward` | Notificar recompensas del reto diario. |
| `drops_events` | Elige qué eventos de drops se envían (ver [Eventos de drops](#eventos-de-drops)). |
| `include_category_in_points` | Añade la categoría del stream a las notificaciones de puntos. |
| `min_points_gain` | Ganancia mínima que dispara una notificación de puntos. |
| `send_daily_reward_card` | Envía la carta de recompensa diaria como foto real. `false` (solo texto) por defecto. |

Todos los flags `notify_*` valen `true` por defecto. Pon cualquiera en `false` para silenciar solo ese tipo de evento.

Recibirás un mensaje por:

*   🚀 Inicio del miner: `notify_startup`
*   💰 Puntos ganados por streamer: `notify_points`
*   👁 Cambios de estado de streamers: `notify_status_change`
*   🎁 Eventos de drops: `drops_events`
*   ❌ Errores: `notify_errors`
*   🎉 Recompensa diaria reclamada (requiere `ClaimDailyReward`): `notify_daily_reward`
*   🔄 Reinicios / detenciones: `notify_restart` (se envía de forma síncrona justo antes de que termine el proceso, así que llega incluso con Ctrl+C)

---

## 🟣 Webhook de Discord

Notificaciones en tiempo real en cualquier canal de Discord mediante un webhook. Sin necesidad de bot.

**Configuración:**

1. En tu servidor de Discord ve a **Configuración del canal → Integraciones → Webhooks**.
2. Pulsa **Nuevo webhook** y copia la URL.
3. Pégala en `config.json` → `Discord.webhook_url`.

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

| Parámetro | Descripción |
| :--- | :--- |
| `webhook_url` | URL del webhook de Discord. |
| `username` | Nombre que mostrará el bot en Discord. |
| `avatar_url` | URL de avatar personalizado (opcional). |
| `notify_points` | Notificar cuando se ganen puntos. |
| `notify_status_change` | Notificar cuando los streamers se conectan / desconectan / son desplazados. |
| `notify_errors` | Notificar errores. |
| `notify_startup` | Enviar un resumen al iniciar. |
| `notify_restart` | Notificar cuando el miner se detiene o reinicia. |
| `notify_daily_reward` | Notificar recompensas del reto diario. |
| `drops_events` | Elige qué eventos de drops se envían (ver [Eventos de drops](#eventos-de-drops)). |
| `include_category_in_points` | Añade la categoría del stream a las notificaciones de puntos. |
| `min_points_gain` | Ganancia mínima que dispara una notificación de puntos. |
| `send_daily_reward_card` | Adjunta la carta de recompensa diaria como imagen. `false` (solo texto) por defecto. |
| `color_*` | Colores del embed en decimal (usa un [conversor de colores](https://www.mathsisfun.com/hexadecimal-decimal-colors.html)). |

Discord envía los mismos tipos de mensajes que Telegram (inicio, puntos con enlace al streamer, inicio de watch / desplazado, online / offline, drops, errores, recompensa diaria, reinicios), cada uno controlado por el flag indicado arriba.

---

## 🎯 Reclamo de recompensa diaria

Revisa y reclama automáticamente el reto diario de gamificación de Kick (recompensa por tiempo de visualización + premio de ruleta) por cuenta, y publica el resultado en Discord y / o Telegram.

**Cómo funciona (sin intervalo fijo de revisión):**

1. Al iniciar, justo después de reclamar, o cuando empieza la ventana de un nuevo día, consulta una vez a Kick cuántos minutos de visualización faltan.
2. A partir de ahí solo cuenta tiempo localmente mientras la cuenta está viendo un stream. Si no hay nada que ver, el reto no puede avanzar, así que no se hace ninguna petición.
3. Cuando el tiempo acumulado alcanza lo que faltaba, vuelve a consultar y reclama automáticamente.
4. Una vez reclamado por el día, deja de llamar a la API hasta que empiece la siguiente ventana.

```json
{ "ClaimDailyReward": false }
```

`ClaimDailyReward` es un simple interruptor on / off (por defecto `false`). Si el evento se publica, y si incluye la imagen de la carta, lo controlan los ajustes propios de cada canal: `notify_daily_reward` y `send_daily_reward_card`.

La notificación muestra la confirmación del reclamo, la rareza de la recompensa (con la imagen de la carta solo si `send_daily_reward_card` es `true`), o, si ya tenías esa carta, los minutos extra de visualización que obtuviste en su lugar.

---

## 🌐 Soporte de proxy

| Tipo | Formato | Ejemplo |
| :--- | :--- | :--- |
| SOCKS5 | `socks5://user:pass@host:port` | `socks5://admin:123@proxy.com:1080` |
| SOCKS5 (sin auth) | `socks5://host:port` | `socks5://proxy.com:1080` |
| HTTP | `http://user:pass@host:port` | `http://admin:123@proxy.com:8080` |
| HTTPS | `https://host:port` | `https://proxy.com:8080` |

El proxy global se aplica a todas las cuentas. Un proxy por cuenta lo sobrescribe.

---

## 📁 Estructura del proyecto

```
Kick_Channel_Points_Miner/
├── main.py                    # Punto de entrada
├── account_manager.py         # Orquestador multi-cuenta con prioridades
├── config.json                # Tu configuración (la creas tú)
├── config.example.json        # Plantilla de configuración
├── localization.py            # Cargador de i18n
├── discord_webhook.py         # Notificador de Discord
├── telegram.py                # Notificador de Telegram
├── memory_monitor.py          # Monitor de uso de memoria
├── requirements.txt           # Dependencias
├── Dockerfile                 # Construcción del contenedor
├── docker-compose.yml         # Compose para Docker / Portainer
├── _websockets/
│   ├── ws_connect.py          # Cliente WebSocket con soporte de proxy
│   └── ws_token.py            # Obtención del token de WebSocket
├── utils/
│   ├── kick_utility.py        # Obtención de Channel / Stream ID
│   ├── get_points_amount.py   # Comprobación del balance de puntos
│   ├── daily_challenge.py     # Reclamo de la recompensa diaria
│   ├── drops_api.py           # Cliente de la API de campañas / progreso / reclamo de drops
│   └── drops_miner.py         # Coordinador de drops (prioridad, cambio, reclamo)
└── lang/
    ├── en.lang                # Mensajes en inglés
    ├── es.lang                # Mensajes en español
    └── ru.lang                # Mensajes en ruso
```

---

## 🐳 Docker y Portainer

La forma recomendada de ejecutar el miner en segundo plano, por ejemplo en un servidor doméstico, un NAS o cualquier máquina con **Portainer**.

**Requisitos:** [Docker](https://docs.docker.com/get-docker/) instalado y un `config.json` válido (copia `config.example.json` y edítalo primero).

### Opción 1: Docker CLI

```bash
# 1. Construir la imagen (desde la raíz del proyecto)
docker build -t kick-channel-points-miner .

# 2. Iniciar el contenedor
docker run -d \
  --name kick-miner \
  --restart unless-stopped \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  kick-channel-points-miner
```

### Opción 2: Docker Compose

```bash
# config.json debe estar en la misma carpeta que docker-compose.yml
docker compose up -d
```

Parar: `docker compose down` · Logs: `docker compose logs -f`

### Opción 3: Portainer (GUI)

Sigue esta guía: <https://github.com/Baillora/Kick_Channel_Points_Miner/issues/4#issuecomment-3944659440>

> **Consejo:** el contenedor se reinicia solo tras un fallo o un reinicio del servidor gracias a `restart: unless-stopped`.

> **Seguridad:** `config.json` **nunca se incluye dentro de la imagen**. Siempre se monta en tiempo de ejecución, así tus tokens se quedan en tu host.

---

## ⚠ Aviso legal

Este software es solo para fines educativos. Úsalo bajo tu propia responsabilidad. El desarrollador no se hace responsable de bloqueos o restricciones en tu cuenta de Kick.com.

Los cambios de este fork se implementan con ayuda de IA y pueden contener errores (ver el aviso al inicio).

---

## 📜 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
