"""The interface every backend implements."""
from __future__ import annotations

from typing import Callable, Optional, Tuple


class Backend:
    """Sends mouse events. Coordinates are global screen coordinates, the same system as Qt (QCursor.pos)."""

    name = "?"
    #: Whether the global cursor position can be read (not on Wayland)
    can_read_cursor = True
    #: (string key of the button label, callable) shown next to the warning so the user can fix it,
    #: e.g. open the permission settings
    fix_action: Optional[Tuple[str, Callable[[], None]]] = None

    def status(self) -> Optional[str]:
        """None = ready; a string = why clicking can't work yet (shown in the warning banner)."""
        return None

    def request_permission(self) -> None:
        """Called on Start so the OS can ask for permission if needed."""

    def move(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class DryBackend(Backend):
    """Sends no real clicks: for trying the UI, or when the real backend failed to start."""

    name = "dry-run"

    def __init__(self, error: Optional[str] = None):
        self.error = error

    def status(self):
        return self.error

    def move(self, x, y):
        pass

    def click(self, x, y, button="left", clicks=1):
        pass


class KeepAwake:
    """Keeps the computer awake / unlocked while running. Default: does nothing."""

    def begin(self, prevent_sleep: bool) -> bool:
        """Returns False if keeping awake was requested but isn't possible."""
        return not prevent_sleep

    def end(self) -> None:
        pass
