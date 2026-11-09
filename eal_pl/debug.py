"""EAL-PL debugging support.

Provides a tracing virtual machine and source-location-aware error reporting
so developers can step through execution and map runtime events back to source
text.
"""

from __future__ import annotations

from .vm import VM


class DebugVM(VM):
    """A VM with execution tracing enabled."""

    def __init__(self, ir, capture_output: bool = True,
                 natives: dict | None = None) -> None:
        super().__init__(ir, capture_output=capture_output, debug=True,
                         natives=natives)

    def run_with_trace(self) -> Any:
        """Run and return the result, printing each executed instruction."""
        return self.run()


def format_source_context(source: str, location, context_lines: int = 2) -> str:
    """Return source lines around ``location`` with a column caret."""
    lines = source.splitlines()
    line = location.line
    start = max(0, line - 1 - context_lines)
    end = min(len(lines), line + context_lines)
    out = []
    for i in range(start, end):
        marker = ">>> " if i == line - 1 else "    "
        out.append(f"{marker}{i + 1:4d}| {lines[i]}")
    if 0 <= line - 1 < len(lines):
        col = max(location.column - 1, 0)
        out.append("     " + " " * col + "^")
    return "\n".join(out)
