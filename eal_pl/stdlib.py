"""EAL-PL standard library.

Native functions exposed to EAL-PL programs. These are implemented in the
host language (Python stdlib) and registered on the VM via
:meth:`VM.register_native`. Programs call them as ordinary functions.
"""

from __future__ import annotations

from typing import Any, Callable


def build_stdlib() -> dict[str, Callable[..., Any]]:
    """Return the standard library as a name -> callable mapping."""
    return {
        "print": _native_print,
        "to_string": _native_to_string,
        "length": _native_length,
    }


def _native_print(*values: Any) -> None:
    """Print values to the VM's captured stdout (host side)."""
    # The VM handles 'print' specially; this is here for completeness and
    # for hosts that call natives directly.
    return None


def _native_to_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _native_length(value: Any) -> int:
    if isinstance(value, str):
        return len(value)
    raise TypeError("length() requires a string")
