import json
import asyncio
import traceback
import random
import time
from typing import Dict, Optional, Callable, Awaitable
from dataclasses import dataclass
import websockets
from websockets.asyncio.client import connect as ws_connect
from loguru import logger
from localization import t


# How long (seconds) without ANY inbound traffic from Kick before the
# connection is considered dead even though the TCP socket never raised
# an exception. Kick's viewer socket is otherwise silent between
# handshakes/pings, so this must stay comfortably above the handshake
# interval (25-35s) to avoid false positives.
STALE_CONNECTION_SECONDS = 90

# A connection must have stayed up at least this long before we treat it
# as evidence the link is healthy and reset the reconnect-attempt
# counter. Without this floor, a connection that opens and then dies
# almost immediately (e.g. the server accepts the socket but then
# rejects the token) would reset the counter every single time,
# letting the reconnect loop retry forever instead of ever reaching
# `on_disconnect`.
MIN_HEALTHY_CONNECTION_SECONDS = 30


@dataclass
class ConnectionState:
    is_connected: bool = False
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5


class KickWebSocket:
    """
    One viewer connection to Kick's websocket.

    Reconnection is centralized in `_reconnect_or_give_up`, which is the
    ONLY place allowed to flip `is_connected` back to True. Every failure
    path (a send failing, recv failing, or the server going silent) goes
    through it, guarded by `_reconnect_lock` so overlapping failures
    (e.g. a send AND the listen loop both fail around the same moment)
    never trigger two reconnects racing each other.

    `on_disconnect` fires exactly once, only when reconnection is
    permanently given up on (attempts exhausted), so callers can rely on
    it to mean "this viewer slot is truly gone and something else must
    be started instead."
    """

    def __init__(
        self,
        data: Dict[str, str],
        proxy: Optional[str] = None,
        on_disconnect: Optional[Callable[[], Awaitable]] = None,
    ):
        self.ws = None
        self.data = data
        self.proxy = proxy
        self.on_disconnect = on_disconnect
        self.state = ConnectionState()
        self.handshake_task: Optional[asyncio.Task] = None
        self.tracking_task: Optional[asyncio.Task] = None
        self.watchdog_task: Optional[asyncio.Task] = None
        self._running = False
        self._closing = False
        self._reconnect_lock = asyncio.Lock()
        self._gave_up = False
        # Any inbound message, including raw "ping" pongs, counts as
        # proof the server still knows about us.
        self._last_inbound_at: float = 0.0
        # When the current/last connection attempt actually opened;
        # used to decide whether it counts as "healthy enough" to reset
        # the reconnect-attempt counter (see MIN_HEALTHY_CONNECTION_SECONDS).
        self._connected_at: float = 0.0

    async def connect(self) -> bool:
        """
        Establish the connection once and then block for the lifetime of
        this viewer, handling every reconnect internally. Returns only
        when the connection is permanently given up on or `disconnect()`
        was called from outside.
        """
        self._closing = False
        ok = await self._connect_once()
        if not ok:
            await self._reconnect_or_give_up("initial connect failed")
        return ok

    async def _connect_once(self) -> bool:
        if not self.data.get("token"):
            logger.error(t("token_must_not_be_empty"))
            return False

        try:
            ch = self.data.get("channelId", "?")
            logger.info(t(
                "websocket_connecting", channel_id=ch
            ))

            ws_url = (
                "wss://websockets.kick.com/viewer/v1/connect"
                f"?token={self.data['token']}"
            )

            ws_kwargs = dict(
                max_size=4096,
                additional_headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )

            if self.proxy:
                try:
                    from websockets.extensions import permessage_deflate  # noqa: F401
                    import python_socks  # noqa: F401
                    from python_socks.async_.asyncio import Proxy

                    proxy = Proxy.from_url(self.proxy)
                    sock = await proxy.connect(
                        dest_host="websockets.kick.com", dest_port=443
                    )
                    ws_kwargs["sock"] = sock
                    ws_kwargs["server_hostname"] = "websockets.kick.com"
                except ImportError:
                    logger.warning(t("proxy_socks_not_installed"))
                except Exception as e:
                    logger.warning(t(
                        "proxy_connection_failed", error=str(e)
                    ))

            self.ws = await ws_connect(ws_url, **ws_kwargs)

            logger.success(t("websocket_connected"))
            self.state.is_connected = True
            self._connected_at = time.monotonic()
            self._last_inbound_at = time.monotonic()

            await self._send_initial_messages()
            await self._start_background_tasks()
            await self._listen_for_messages()

            return True

        except Exception as e:
            logger.error(t(
                "websocket_connection_failed", error=str(e)
            ))
            logger.debug(t(
                "connection_traceback",
                traceback=traceback.format_exc(),
            ))
            self.state.is_connected = False
            return False

    async def _send_initial_messages(self):
        await self._send_handshake()
        await self._send_ping()

    async def _start_background_tasks(self):
        self._running = True
        self.handshake_task = asyncio.create_task(
            self._handshake_loop()
        )
        self.tracking_task = asyncio.create_task(
            self._tracking_loop()
        )
        self.watchdog_task = asyncio.create_task(
            self._watchdog_loop()
        )

    async def _handshake_loop(self):
        while self._running and self.state.is_connected:
            try:
                await asyncio.sleep(random.uniform(25, 35))
                if self.state.is_connected:
                    await self._send_handshake()
                    await self._send_ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(t(
                    "handshake_loop_error", error=str(e)
                ))
                break

    async def _tracking_loop(self):
        while self._running and self.state.is_connected:
            try:
                await asyncio.sleep(random.uniform(9.5, 12.5))
                if self.state.is_connected:
                    await self._send_user_event()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(t(
                    "tracking_loop_error", error=str(e)
                ))
                break

    async def _watchdog_loop(self):
        """
        Safety net for a "zombie" socket: the TCP connection never raises
        an exception, but Kick has stopped answering (no message, not
        even a raw "ping", for STALE_CONNECTION_SECONDS). This is what
        catches the case a plain send-failure/recv-failure check misses,
        since neither ever fires on a half-open connection.
        """
        try:
            while self._running and self.state.is_connected:
                await asyncio.sleep(15)
                if not self.state.is_connected:
                    return
                idle = time.monotonic() - self._last_inbound_at
                if idle > STALE_CONNECTION_SECONDS:
                    logger.warning(t(
                        "websocket_stale_connection",
                        seconds=int(idle),
                    ))
                    self.state.is_connected = False
                    await self._reconnect_or_give_up(
                        t("websocket_stale_connection", seconds=int(idle))
                    )
                    return
        except asyncio.CancelledError:
            pass

    async def _listen_for_messages(self):
        try:
            while self.state.is_connected and self._running:
                message = await self.ws.recv()
                self._last_inbound_at = time.monotonic()
                await self._handle_message(message)
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(t(
                "message_listening_error", error=str(e)
            ))
            self.state.is_connected = False
            await self._reconnect_or_give_up(str(e))
        except Exception as e:
            logger.error(t(
                "message_listening_error", error=str(e)
            ))
            self.state.is_connected = False
            await self._reconnect_or_give_up(str(e))

    async def _handle_message(self, message):
        try:
            if isinstance(message, (bytes, bytearray)):
                msg = message.decode("utf-8", errors="ignore")
            else:
                msg = str(message)

            if not msg or msg.strip() == "":
                return

            if msg.strip() == "ping":
                await self._send_pong()
                return

            try:
                parsed = json.loads(msg)
            except json.JSONDecodeError:
                return

            msg_type = parsed.get("type", "unknown")
            logger.debug(t(
                "received_message_type", type=msg_type
            ))

            if msg_type == "channel_handshake":
                ch_id = None
                data_msg = parsed.get("data", {})
                if isinstance(data_msg, dict):
                    message_inner = data_msg.get("message", {})
                    if isinstance(message_inner, dict):
                        ch_id = message_inner.get("channelId")
                if ch_id:
                    logger.info(t(
                        "channel_handshake_received",
                        channel_id=ch_id,
                    ))

            elif msg_type == "ping":
                await self._send_pong()

            elif msg_type == "pong":
                pass

            elif msg_type == "error":
                err_data = parsed.get("data", {})
                err = (
                    err_data.get("message", "Unknown")
                    if isinstance(err_data, dict)
                    else "Unknown"
                )
                logger.error(t("websocket_error", error=err))

            elif msg_type == "user_event":
                pass

        except Exception as e:
            logger.error(t(
                "message_handling_error", error=str(e)
            ))

    async def _reconnect_or_give_up(self, reason: str = ""):
        """
        Single entry point for every reconnection attempt. Guarded by a
        lock so a send failure and a recv failure discovered at the same
        moment never spawn two competing reconnect sequences.
        """
        if self._closing or self._gave_up:
            return
        if self._reconnect_lock.locked():
            # Another failure path is already handling this; don't pile on.
            return

        async with self._reconnect_lock:
            if self._closing or self._gave_up:
                return

            await self._cleanup_tasks()

            while (
                not self._closing
                and self.state.reconnect_attempts
                < self.state.max_reconnect_attempts
            ):
                self.state.reconnect_attempts += 1
                logger.info(t(
                    "attempting_reconnect",
                    attempt=self.state.reconnect_attempts,
                    max=self.state.max_reconnect_attempts,
                ))

                delay = min(
                    5 * (2 ** (self.state.reconnect_attempts - 1)),
                    120,
                )
                logger.info(t("reconnect_delay", delay=delay))
                await asyncio.sleep(delay)

                if self._closing:
                    return

                connected_ok = await self._connect_once()
                # `_connect_once` blocks inside `_listen_for_messages` for
                # as long as this connection stays healthy, so by the
                # time it returns, that connection has already ended one
                # way or another (its own failure path already tried to
                # call `_reconnect_or_give_up` too, but found the lock
                # held by this very call and backed off — so picking the
                # next attempt back up here, in the same loop, is the
                # only place it still happens).
                #
                # A connection that stayed up at least
                # MIN_HEALTHY_CONNECTION_SECONDS is treated as proof the
                # link itself is fine (whatever killed it was transient),
                # so the attempt counter is reset before continuing —
                # this failure shouldn't count against the budget of
                # attempts reserved for a genuinely broken link. A
                # connection that opened and then died almost immediately
                # does NOT reset the counter — otherwise a socket that is
                # accepted but then instantly rejected (bad token, banned
                # proxy, etc.) would retry forever and `on_disconnect`
                # would never fire.
                if connected_ok:
                    lived_for = time.monotonic() - self._connected_at
                    if lived_for >= MIN_HEALTHY_CONNECTION_SECONDS:
                        self.state.reconnect_attempts = 0
                    else:
                        logger.warning(t(
                            "websocket_short_lived_connection",
                            seconds=round(lived_for, 1),
                        ))
                if self._closing or self._gave_up:
                    return

            if not self._closing:
                logger.error(t("max_reconnection_attempts"))
                self._gave_up = True
                await self._disconnect_internal()
                if self.on_disconnect:
                    await self.on_disconnect()

    async def _cleanup_tasks(self):
        self._running = False
        for task in (self.handshake_task, self.tracking_task, self.watchdog_task):
            if task and not task.done() and task is not asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.handshake_task = None
        self.tracking_task = None
        self.watchdog_task = None

    async def _disconnect_internal(self):
        self.state.is_connected = False
        await self._cleanup_tasks()
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def disconnect(self):
        """External, intentional shutdown: never triggers a reconnect."""
        self._closing = True
        await self._disconnect_internal()
        logger.info(t("websocket_closed"))

    async def _send_handshake(self):
        if not self.state.is_connected:
            return
        payload = {
            "type": "channel_handshake",
            "data": {
                "message": {
                    "channelId": int(
                        self.data.get("channelId", 0)
                    ),
                }
            },
        }
        try:
            await self.ws.send(
                json.dumps(payload)
            )
            logger.debug(t(
                "sent_handshake",
                channel_id=self.data.get("channelId", "?"),
            ))
        except Exception as e:
            logger.error(t(
                "failed_send_handshake", error=str(e)
            ))
            self.state.is_connected = False
            asyncio.ensure_future(self._reconnect_or_give_up(str(e)))

    async def _send_ping(self):
        if not self.state.is_connected:
            return
        try:
            await self.ws.send(
                json.dumps({"type": "ping"})
            )
            logger.debug(t("sent_ping"))
        except Exception as e:
            logger.error(t("failed_send_ping", error=str(e)))
            self.state.is_connected = False
            asyncio.ensure_future(self._reconnect_or_give_up(str(e)))

    async def _send_pong(self):
        if not self.state.is_connected:
            return
        try:
            await self.ws.send(
                json.dumps({"type": "pong"})
            )
        except Exception:
            pass

    async def _send_user_event(self):
        if not self.state.is_connected:
            return
        payload = {
            "type": "user_event",
            "data": {
                "message": {
                    "name": "tracking.user.watch.livestream",
                    "channel_id": int(
                        self.data.get("channelId", 0)
                    ),
                    "livestream_id": int(
                        self.data.get("streamId", 0)
                    ),
                }
            },
        }
        try:
            await self.ws.send(
                json.dumps(payload)
            )
            logger.debug(t(
                "sent_user_event",
                channel_id=self.data.get("channelId", "?"),
                stream_id=self.data.get("streamId", "?"),
            ))
        except Exception as e:
            logger.error(t(
                "failed_send_user_event", error=str(e)
            ))
            self.state.is_connected = False
            asyncio.ensure_future(self._reconnect_or_give_up(str(e)))
