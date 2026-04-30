import asyncio
import logging
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    List,
    Optional,
    ParamSpec,
    Union,
    get_type_hints,
    get_origin,
    get_args,
)
import types

from fastapi import (
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

P = ParamSpec("P")

HandlerType = Callable[Concatenate["WebSocketManager", P], Awaitable[None]]
HandlerTypeNoTake = Callable[["WebSocketManager"], Awaitable[None]]

import inspect
from typing import get_type_hints


def _validate_and_cast(func: HandlerType, kwargs: dict) -> dict:
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    validated = {}

    for name, param in sig.parameters.items():
        if name == "ws":
            continue

        if name not in kwargs:
            if param.default is inspect.Parameter.empty:
                raise TypeError(f"Missing required argument: '{name}'")
            continue

        value = kwargs[name]
        expected_type = hints.get(name)

        if expected_type:
            origin = get_origin(expected_type)
            args = get_args(expected_type)

            is_optional = (origin is Union and type(None) in args) or (
                origin is types.UnionType and type(None) in args
            )

            if is_optional:
                inner_types = [a for a in args if a is not type(None)]
                actual_type = inner_types[0] if len(inner_types) == 1 else None
            else:
                actual_type = expected_type

            if value is None and is_optional:
                validated[name] = value
                continue

            if actual_type is not None:
                check_type = get_origin(actual_type) or actual_type

                if (
                    isinstance(check_type, type)
                    and check_type is not Union
                    and not isinstance(check_type, types.UnionType)
                ):
                    if not isinstance(value, check_type):
                        if check_type is str:
                            raise TypeError(
                                f"Argument '{name}' expected str, got {type(value).__name__}"
                            )
                        elif issubclass(check_type, BaseModel):
                            try:
                                if isinstance(value, dict):
                                    value = check_type.model_validate(value)
                                elif isinstance(value, list):
                                    value = check_type.model_validate(
                                        dict(zip(check_type.model_fields, value))
                                    )
                                else:
                                    value = check_type.model_validate(value)
                            except (ValueError, TypeError) as e:
                                raise TypeError(
                                    f"Argument '{name}' expected {check_type.__name__}, "
                                    f"got {type(value).__name__}: {e}"
                                )
                        else:
                            try:
                                value = check_type(value)
                            except (ValueError, TypeError):
                                raise TypeError(
                                    f"Argument '{name}' expected {check_type.__name__}, "
                                    f"got {type(value).__name__}"
                                )

        validated[name] = value

    return validated


class EventRouter:
    def __init__(self):
        self.handlers: dict[str, HandlerType] = {}
        self.on_entry: list[HandlerTypeNoTake] = []  # Added for connection
        self.on_exit: list[HandlerTypeNoTake] = []

    def on(self, event_type: str):
        def decorator(func: HandlerType):
            logger.info(f"Signed {event_type}")
            self.handlers[event_type] = func
            return func
        return decorator

    def on_connect(self):
        """Decorator to register a function to run when a client connects."""
        def decorator(func: HandlerTypeNoTake):
            logger.info(f"Signed {func.__name__} as on connect")
            self.on_entry.append(func)
            return func
        return decorator

    def on_disconnect(self):
        def decorator(func: HandlerTypeNoTake):
            logger.info(f"Signed {func.__name__} as on disconnect")
            self.on_exit.append(func)
            return func
        return decorator

    async def connect(self, ws_manager: "WebSocketManager"):
        """Executes all registered on_connect handlers."""
        if self.on_entry:
            results = await asyncio.gather(
                *(handler(ws_manager) for handler in self.on_entry),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.error("on_connect handler failed", exc_info=r)

    async def dispatch(self, ws_manager: "WebSocketManager", data: dict):
        event_type = data.get("t")
        if not event_type or not isinstance(event_type, str):
            logger.warning("type not found")
            return

        handler = self.handlers.get(event_type)
        if not handler:
            logger.warning(f"handler for '{event_type}' not found")
            return

        data = dict(data)
        data.pop("t", None)

        try:
            validated_kwargs = _validate_and_cast(handler, data)
            await handler(ws_manager, **validated_kwargs)
        except TypeError as e:
            logger.error(f"Validation error for '{event_type}': {e}")
        except Exception:
            logger.exception("Something went wrong")

    async def disconnect(self, ws_manager: "WebSocketManager"):
        if self.on_exit:
            results = await asyncio.gather(
                *(handler(ws_manager) for handler in self.on_exit),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.error("on_exit handler failed", exc_info=r)

router = EventRouter()

# Global connection manager instance
connection_manager = None


def get_connection_manager():
    """Get or create the global connection manager"""
    global connection_manager
    if connection_manager is None:
        connection_manager = ConnectionManager()
    return connection_manager


class ConnectionManager:
    """Manages all active WebSocket connections for users."""

    def __init__(self):
        # Maps user_id -> List[WebSocketManager] (allows multiple sessions per user)
        self.connections: dict[str, List["WebSocketManager"]] = {}

    def add(self, user_id: str, ws: "WebSocketManager"):
        """Register a new connection for a user."""
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(ws)

    def remove(self, user_id: str, ws: "WebSocketManager"):
        """Unregister a specific connection for a user."""
        if user_id in self.connections:
            self.connections[user_id] = [
                conn for conn in self.connections[user_id] if conn != ws
            ]
            # Remove the key if no more connections for this user
            if not self.connections[user_id]:
                self.connections.pop(user_id, None)

    def get(self, user_id: str) -> List["WebSocketManager"]:
        """Get all connections for a user."""
        return self.connections.get(user_id, [])

    def exists(self, user_id: str) -> bool:
        """Check if there are any active connections for a user."""
        return user_id in self.connections and len(self.connections[user_id]) > 0

    def get_all_users(self) -> List[str]:
        """Get list of all connected user IDs."""
        return list(self.connections.keys())

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all sessions of a specific user."""
        connections = self.get(str(user_id))
        for conn in connections:
            try:
                await conn.websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send message to {user_id} session: {conn}, error: {e}"
                )

    async def broadcast(self, message: dict, exclude: List[str] = []):
        """Send a message to all online users (optionally excluding some)."""
        for uid, connections in self.connections.items():
            if uid not in exclude:
                for conn in connections:
                    try:
                        await conn.websocket.send_json(message)
                    except Exception:
                        pass


class WebSocketManager:
    """Represents a single user's WebSocket connection for messaging."""

    REPEAT_SIGNAL = 30  # Seconds to give the client to ping to repeat the number of seconds before disconnecting
    PING_TTL = (
        REPEAT_SIGNAL * 3
    )  # Seconds between expected pings to keep connection alive
    REDIS_ONLINE_TTL = REPEAT_SIGNAL * 4  # TTL for Redis online status

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.user = "root"
        self.message_task: asyncio.Task | None = None
        self.watchdog_task: asyncio.Task | None = None
        self.cm = get_connection_manager()
        self.last_ping = asyncio.get_event_loop().time()
        self._closing = False  # Flag to prevent duplicate close attempts
        self._notified_online = False  # Flag to send online notification only once
        self._cleanup_lock = asyncio.Lock()
        self.cleaned_user = False
        self.logger = logging.getLogger(f"{self.user}")

    async def start(self):
        """Entry point to manage WebSocket lifecycle."""
        await self.websocket.accept()
        self.cm.add(str(self.user), self)

        logger.info(f"User {self.user} connected via WebSocket")

        self.message_task = asyncio.create_task(self.handle_messages())
        self.watchdog_task = asyncio.create_task(self.ping_watchdog())

        self.last_ping = asyncio.get_event_loop().time()
        await self.websocket.send_json(
            {"t": "connection_success", "signal": self.REPEAT_SIGNAL}
        )
        await router.connect(self)

        try:
            done, pending = await asyncio.wait(
                [self.message_task, self.watchdog_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.warning(f"WebSocket error: {e}")
        finally:
            await self.cleanup()

    async def clean_user(self):
        async with self._cleanup_lock:
            if self.cleaned_user:
                return
            self.cleaned_user = True

            user_id = str(self.user)

            connections = self.cm.get(user_id)
            if self in connections:
                self.cm.remove(user_id, self)
            await router.disconnect(self)

            await asyncio.sleep(1)

    async def ping_watchdog(self):
        """Disconnect if the client hasn't sent a ping recently."""
        while True:
            await asyncio.sleep(5)  # check every 5 seconds
            now = asyncio.get_event_loop().time()
            if now - self.last_ping > self.PING_TTL:
                logger.warning(
                    f"No ping from {self.user} in {self.PING_TTL}s - disconnecting"
                )
                self._closing = True

                await self.clean_user()

                try:
                    await self.websocket.close(code=1001, reason="Ping timeout")
                except Exception:
                    pass
                break

    async def handle_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            while True:
                data: dict = await self.websocket.receive_json()
                await router.dispatch(self, data)

        except WebSocketDisconnect:
            logger.info(f"User {self.user} disconnected")
        except Exception as e:
            logger.warning(f"Message handling error: {e}")

    async def cleanup(self):
        """Cancel tasks and close WebSocket."""
        if self._closing:
            return  # Already closing/closed

        self._closing = True

        if self.message_task and not self.message_task.done():
            self.message_task.cancel()
            try:
                await self.message_task
            except asyncio.CancelledError:
                pass

        if self.watchdog_task and not self.watchdog_task.done():
            self.watchdog_task.cancel()
            try:
                await self.watchdog_task
            except asyncio.CancelledError:
                pass

        try:
            await self.clean_user()
            logger.info(f"User {self.user} connection cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup error during removal: {e}")

        try:
            await self.websocket.close()
        except Exception:
            # Connection might already be closed, ignore
            pass

    async def emit(self, event: str, data: Optional[Union[dict, BaseModel, list]] = None):
        """Send an event to this WebSocket client."""
        payload = {"t": event}
        if data:
            if isinstance(data, BaseModel):
                data = data.model_dump(mode="json")
            payload.update(data)
        try:
            await self.cm.broadcast(payload)
        except Exception as e:
            logger.warning(f"Failed to send message to {self.user}: {e}")


@router.on("ping")
async def pong(ws: WebSocketManager):
    ws.last_ping = asyncio.get_event_loop().time()
