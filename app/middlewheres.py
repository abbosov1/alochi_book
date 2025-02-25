from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:

        # Логируем входящее событие
        print(f"[Middleware] Получено событие: {event}")
        result = await handler(event, data)
        # Логируем завершение обработки события
        print("[Middleware] Событие обработано")
        return result
