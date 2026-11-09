"""EAL-PL package system (minimal).

Loads EAL-PL source modules from a search path, compiles them, and exposes
their top-level bindings. This is intentionally small: modules are files with
a `.eal` extension; a "package" is a directory of modules. The loader is
deterministic (sorted file order) for reproducibility.
"""

from __future__ import annotations

import os
from typing import Any

from .compiler import Compiler
from .vm import VM


class Package:
    """A compiled EAL-PL module/package.

    Attributes:
        name: Module name (file stem).
        source: Original source text.
        ir: Compiled intermediate representation.
        globals: Top-level bindings after execution.
    """

    def __init__(self, name: str, source: str, ir, globals_: dict[str, Any]):
        self.name = name
        self.source = source
        self.ir = ir
        self.globals = globals_


class PackageLoader:
    def __init__(self, search_paths: list[str] | None = None,
                 file_extension: str = ".eal") -> None:
        self.search_paths = list(search_paths or ["."])
        self.file_extension = file_extension
        self._cache: dict[str, Package] = {}

    def resolve(self, module_name: str) -> str | None:
        for base in self.search_paths:
            for suffix in (module_name.replace(".", "/") + self.file_extension,
                           module_name + self.file_extension):
                path = os.path.join(base, suffix)
                if os.path.isfile(path):
                    return path
        return None

    def load(self, module_name: str, vm: VM | None = None) -> Package:
        if module_name in self._cache:
            return self._cache[module_name]
        path = self.resolve(module_name)
        if path is None:
            raise FileNotFoundError(f"module not found: {module_name}")
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        vm = vm or VM(Compiler().compile(__import__("eal_pl.parser", fromlist=["x"]).Parser(
            __import__("eal_pl.tokens", fromlist=["x"]).Lexer(source).tokenize()).parse()))
        pkg = Package(module_name, source, vm.ir, dict(vm.globals))
        self._cache[module_name] = pkg
        return pkg
