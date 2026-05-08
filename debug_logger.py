from __future__ import annotations

from datetime import datetime


class DebugLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._handlers = []

    def add_handler(self, handler):
        self._handlers.append(handler)

    def log(self, tag: str, message: str) -> None:
        line = f"[{tag}] {message}"
        self.lines.append(line)
        for h in self._handlers:
            h(line)

    def get_text(self) -> str:
        return "\n".join(self.lines)

    def clear(self) -> None:
        self.lines.clear()

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Debug log {datetime.now().isoformat()}\n")
            f.write(self.get_text())
