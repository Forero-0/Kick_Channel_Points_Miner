# 🟢 Kick Channel Points Miner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> [🇬🇧 **Read in English**](README.md) • [🇷🇺 **Читать на русском языке**](README_RU.md)

Un potente bot asíncrono para farmear automáticamente puntos de canal en **Kick.com**. Incluye control avanzado por Telegram y mecanismos para sortear Cloudflare.

---

## ✨ Características

*   **👥 Soporte Multi-Cuenta:** Farmea puntos con 10+ cuentas simultáneamente, cada una con su propia lista de streamers y límites.
*   **🎯 Sistema de Prioridades:** Los streamers se priorizan por su posición en el `config.json`. Los de mayor prioridad reemplazan a los de menor cuando están en vivo.
*   **🔒 Límites Concurrentes:** Ajusta `max_concurrent` por cuenta para controlar cuántos streamers se ven a la vez y evitar errores 403.
*   **🌐 Proxy SOCKS5/HTTP:** Soporte global o por cuenta para evitar bloqueos por IP.
*   **🛡️ Bypass de Cloudflare:** Gestión de sesiones basada en `curl_cffi` con reintentos automáticos ante 403.
*   **📱 Bot de Telegram:**
    *   **Sistema Owner/Guest:** El propietario tiene control total; los invitados solo pueden ver estado.
    *   **Vistas Multi-Cuenta:** `/status`, `/balance`, `/accounts` muestran información por cuenta.
    *   **Notificaciones en vivo:** Avisos sobre puntos farmed y errores.
    *   **Control remoto:** Reinicia el miner desde Telegram.
*   **🌐 Multilenguaje:** Soporta Inglés y Ruso (y esta traducción al Español).
*   **📉 Registro Inteligente:** Salida de consola limpia con modo Debug opcional.
*   **♻️ Seguro en memoria:** Reutiliza y cierra sesiones correctamente — sin fugas durante ejecuciones largas.

---

## 🚀 Instalación

1.  **Clona o descarga** el repositorio:
    ```bash
    git clone https://github.com/Baillora/Kick_Channel_Points_Miner.git
    cd Kick_Channel_Points_Miner
    ```

2.  **Instala dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configura**: Renombra `config.example.json` a `config.json` y complétalo (ver más abajo).

---

## ⚙️ Configuración (`config.json`)

### Formato Multi-Cuenta (Recomendado)

```json
{
  "Language": "en",
  "Debug": false,

  "Telegram": {
    "enabled": false,
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_USER_ID",
    "allowed_users": [123456789]
  },

  "Discord": {
    "enabled": false,
    "webhook_url": "https://discord.com/api/webhooks/XXXX/YYYY",
    "username": "Baillora KickMiner",
    "avatar_url": "",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "min_points_gain": 10,
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

### Formato legado (aún soportado)
El antiguo formato de una sola cuenta se convierte automáticamente:

```json
{
  "Language": "en",
  "Debug": false,
  "Telegram": { "enabled": false, "bot_token": "", "chat_id": "", "allowed_users": [] },
  "Private": { "token": "YOUR_KICK_TOKEN" },
  "Streamers": ["stream1", "stream2", "stream3"],
  "Max_active_channels": 5
}
```

---

### Descripción de parámetros:

*   **`Language`**: Ajusta a `"en"` o `"ru"` (o `"es"` para esta traducción).
*   **`Debug`**: `true` para logs detallados, `false` para salida limpia.
*   **`Telegram`**:
    *   `bot_token`: Consíguelo de @BotFather.
    *   `chat_id`: Tu ID personal de Telegram (serás el **Owner**).
    *   `allowed_users`: Lista de IDs que pueden ver estado/balance (Guests).
*   **`Proxy.enabled`**: Activa proxy global para todas las cuentas.
    *   `Proxy.url`: URL del proxy (`socks5://`, `http://`, `https://`).
*   **`Check_interval`**: Segundos entre comprobaciones de estado (por defecto: `120`).
*   **`Reconnect_cooldown`**: Segundos antes de reintentar conexión (por defecto: `600`).
*   **`Connection_stagger_min/max`**: Rango de retraso en segundos entre conexiones a streamers.
*   **`👥 Parámetros de cuenta`**:
    *   `alias`: Nombre para la cuenta.
    *   `token`: Token de Kick (Bearer token).
    *   `proxy`: Proxy por cuenta (sobrescribe el global). Usa `null` para el global.
    *   `streamers`: Lista ordenada de nombres (posición = prioridad, índice 0 = máximo).
    *   `max_concurrent`: Número máximo de streamers a ver simultáneamente.

---

## 🎯 Cómo funcionan las prioridades
```
Config: ["streamer1", "streamer2", "streamer3", "streamer4"]
         Prioridad 0  Prioridad 1  Prioridad 2  Prioridad 3
         (Más alta)                               (Más baja)

max_concurrent: 2
```
Tiempo | Evento | Viendo
| :--- | :--- | :--- |
T0 | streamer2 & streamer3 en vivo | `[streamer2, streamer3]`
T1 | streamer1 sale en vivo (más prioridad) | `[streamer1, streamer2]` ← streamer3 desplazado!
T2 | streamer1 se desconecta | `[streamer2, streamer3]` ← streamer3 vuelve
T3 | streamer4 sale en vivo | `[streamer2, streamer3]` ← streamer4 espera (límite alcanzado)

---

### 🔑 Cómo obtener tu token de Kick

1.  Inicia sesión en **Kick.com** en tu navegador.
2.  Pulsa `F12` para abrir las Herramientas de Desarrollador.
3.  Ve a la pestaña **Network**.
4.  Actualiza la página (`F5`).
5.  Haz clic en cualquier petición que aparezca (p. ej. `auth`).
6.  En la panel derecho, abre **Headers** y busca **Request Headers**.
7.  Encuentra la línea `authorization`.
8.  Copia la cadena larga **después** de la palabra `Bearer`. Tiene formato `123456789|************************************`.
9.  Pega esa cadena en tu `config.json` en el campo `"token"`.

## 🎮 Uso

Ejecuta el miner:
```bash
python main.py
```

El bot:

1. Cargará todas las cuentas del config
2. Comprobará qué streamers están online
3. Conectará a los top N (por prioridad) para cada cuenta
4. Rebalanceará dinámicamente cuando cambien estados
5. Se reiniciará automáticamente en fallos

### 📱 Comandos de Telegram

| Comando | Descripción | Permiso |
| :--- | :--- | :--- |
| `/start` | Inicializa el bot y el teclado | Todos |
| `/status` | Ver streamers activos y uptime | Todos |
| `/balance` | Comprobar puntos farmed por canales | Todos |
| `/accounts` | Resumen de todas las cuentas | Todos |
| `/help` | Mostrar comandos disponibles | Todos |
| `/restart` | **Reiniciar el proceso del miner** | **Solo Owner** |
| `/language` | Cambiar idioma del bot (`en`/`ru`) | **Solo Owner** |

---

### 🟣 Webhook de Discord

Envía notificaciones en tiempo real a cualquier canal de Discord mediante webhooks – ¡sin necesidad de bot!

**Configuración:**
1. En tu servidor Discord: **Configuración del canal → Integraciones → Webhooks**
2. Crea un nuevo webhook y copia la URL
3. Pégala en `config.json` → `Discord.webhook_url`

**Ejemplo de configuración:**
```json
{
  "Discord": {
    "enabled": true,
    "webhook_url": "https://discord.com/api/webhooks/XXXX/YYYY",
    "username": "Baillora KickMiner",
    "avatar_url": "",
    "notify_points": true,
    "notify_status_change": true,
    "notify_errors": true,
    "notify_startup": true,
    "min_points_gain": 10,
    "color_success": 3461464,
    "color_info": 5793266,
    "color_warning": 16763904,
    "color_error": 15746887
  }
}
```

| Parámetro | Descripción |
| :--- | :--- |
| `webhook_url` | URL del webhook de Discord |
| `username` | Nombre que mostrará el bot en Discord |
| `avatar_url` | URL de avatar (opcional) |
| `notify_points` | Notificar cuando se ganen puntos |
| `notify_status_change` | Notificar cambios de estado de streamers |
| `notify_errors` | Notificar errores |
| `notify_startup` | Resumen al iniciar |
| `min_points_gain` | Umbral mínimo para notificar |
| `color_*` | Colores en decimal (usar un conversor de hex a decimal)

Notificaciones incluyen:

* 🚀 Resumen de inicio con todas las cuentas
* 💰 Puntos ganados (con enlace al streamer)
* ▶️ Inicio de watch / ⏹ Desplazamiento por prioridad
* 🟢 Streamer online / 🔴 Streamer offline
* ❌ Reportes de errores
* 🔄 Notificaciones de reinicio

---

### 🎯 Reclamo de Recompensa Diaria

Revisa y reclama automáticamente el reto diario de gamificación de Kick (recompensa por tiempo de visualización + premio de ruleta), por cuenta, y puede publicar el resultado en Discord y/o Telegram.

**Cómo funciona — sin intervalo fijo de revisión:**
1. Al iniciar (o justo después de reclamar, o cuando empieza la ventana de un nuevo día), consulta una vez la API de Kick para saber cuántos minutos de visualización faltan.
2. A partir de ahí, solo cuenta tiempo localmente mientras la cuenta está viendo efectivamente un stream. Si no se está viendo nada, el reto tampoco puede avanzar del lado de Kick, así que no llama a la API durante ese tiempo muerto.
3. Cuando el tiempo acumulado alcanza lo que faltaba, vuelve a consultar — si ya está listo, lo reclama automáticamente y registra/notifica el resultado.
4. Una vez reclamado por el día, deja de tocar la API por completo hasta que termine la ventana del reto actual, y solo vuelve a revisar cuando empiece la siguiente — sin peticiones desperdiciadas ni consultas innecesarias.

**Configuración:**
```json
{
  "ClaimDailyReward": {
    "enabled": false,
    "notify_discord": true,
    "notify_telegram": true
  }
}
```

| Parámetro | Descripción |
| :--- | :--- |
| `enabled` | Activa/desactiva toda la función. Desactivado por defecto. |
| `notify_discord` | Publica la recompensa reclamada en Discord (usa la config del webhook de `Discord` de arriba). |
| `notify_telegram` | Publica la recompensa reclamada en Telegram (envía la carta de la recompensa como foto). |

Cuando se reclama una recompensa, la notificación muestra:
* 🎉 Confirmación de que el reto fue reclamado
* 🏆 La rareza de la recompensa, con la imagen de la carta adjunta (cuando es una carta nueva)
* 🎁 O, si ya tenías esa carta, cuántos minutos extra de visualización obtuviste para tu próximo nivel

---

## 🌐 Soporte de Proxy

| Tipo | Formato | Ejemplo |
| :--- | :--- | :--- |
| SOCKS5 | `socks5://user:pass@host:port` | `socks5://admin:123@proxy.com:1080` |
| SOCKS5 (sin auth) | `socks5://host:port` | `socks5://proxy.com:1080` |
| HTTP | `http://user:pass@host:port` | `http://admin:123@proxy.com:8080` |
| HTTPS | `https://host:port` | `https://proxy.com:8080` |

El proxy global se aplica a todas las cuentas. El proxy por cuenta lo sobreescribe.

---

## 📁 Estructura del proyecto

```
Kick_Channel_Points_Miner/
├── main.py                    # Punto de entrada
├── account_manager.py         # Orquestador multi-cuenta con prioridades
├── config.json                # Configuración
├── localization.py            # Cargador de i18n
├── requirements.txt           # Dependencias
├── _websockets/
│   ├── ws_connect.py          # Cliente WebSocket con soporte proxy
│   └── ws_token.py            # Obtención de token WS
├── utils/
│   ├── kick_utility.py        # Obtención de Channel/Stream ID
│   └── get_points_amount.py   # Comprobación de balance de puntos
├── tg_bot/
│   ├── bot.py                 # Bot de Telegram con soporte multi-cuenta
│   └── lang/
│       ├── en.lang            # Strings en inglés
│       └── ru.lang            # Strings en ruso
└── lang/
    ├── en.lang                # Mensajes en inglés
    └── ru.lang                # Mensajes en ruso
```

---

## 🐳 Docker & Despliegue con Portainer

Esta es la forma recomendada para ejecutar el miner en segundo plano.

### Requisitos previos
* [Docker](https://docs.docker.com/get-docker/) instalado (Desktop o Engine).
* Un `config.json` válido (copia `config.example.json` y edítalo).

---

### Opción 1 – Docker CLI (rápido)

```bash
# 1. Construir la imagen (ejecutar desde la raíz del proyecto)
docker build -t kick-channel-points-miner .

# 2. Iniciar el contenedor
docker run -d \
  --name kick-miner \
  --restart unless-stopped \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  kick-channel-points-miner
```

---

### Opción 2 – Docker Compose

```bash
# Asegúrate de que config.json esté en la misma carpeta que docker-compose.yml
docker compose up -d
```

Parar: `docker compose down`
Ver logs: `docker compose logs -f`

---

### Opción 3 – Portainer (GUI, para principiantes)

https://github.com/Baillora/Kick_Channel_Points_Miner/issues/4#issuecomment-3944659440

> **Consejo:** Portainer auto-reinicia el contenedor en caso de fallo o reinicio del servidor gracias a `restart: unless-stopped`.

---

## ⚠️ Aviso

Este software es para fines educativos. Úsalo bajo tu propia responsabilidad. El desarrollador no se hace responsable por bloqueos o sanciones en Kick.com.

---

## 📜 Licencia

Este proyecto está bajo la licencia MIT — ver el archivo [LICENSE](LICENSE) para más detalles.