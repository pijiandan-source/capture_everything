from __future__ import annotations

from datetime import datetime
import traceback


class DebugLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._handlers = []
        self.debug_enabled = False

    def add_handler(self, handler):
        self._handlers.append(handler)
        for line in self.lines:
            handler(line)

    def set_debug(self, enabled: bool) -> None:
        self.debug_enabled = enabled

    def _emit(self, level: str, module: str, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}][{level}][{module}] {message}"
        self.lines.append(line)
        for h in self._handlers:
            h(line)

    def log(self, tag: str, message: str) -> None:
        self.info(tag, message)

    def info(self, module: str, message: str) -> None:
        self._emit("INFO", module, message)

    def debug(self, module: str, message: str) -> None:
        if self.debug_enabled:
            self._emit("DEBUG", module, message)

    def warning(self, module: str, message: str) -> None:
        self._emit("WARN", module, message)

    def error(self, module: str, message: str) -> None:
        self._emit("ERROR", module, message)

    def exception(self, module: str, message: str, exc: BaseException | None = None) -> None:
        self._emit("ERROR", module, message)
        if self.debug_enabled:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else traceback.format_exc()
            for line in tb.rstrip().splitlines():
                self._emit("DEBUG", module, line)

    def get_text(self) -> str:
        return "\n".join(self.lines)

    def clear(self) -> None:
        self.lines.clear()

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Debug log {datetime.now().isoformat()}\n")
            f.write(self.get_text())
