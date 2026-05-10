#!/usr/bin/env python3
"""F05: Module-boundary enforcement via AST walking.

Scans every .py file under ``src/jumlaos/`` and rejects direct imports
between sibling modules (mali <-> talab <-> makhzen). Cross-module
communication must go through ``jumlaos.core.events`` or
``jumlaos.core.services``.

Exit code 0 = clean, 1 = violations found.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Sibling modules that must not import from each other.
MODULES = {"mali", "talab", "makhzen"}

# Allowed cross-cutting packages that any module may import from.
ALLOWED = {"jumlaos.core", "jumlaos.shared", "jumlaos.config", "jumlaos.logging"}

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "jumlaos"


def _module_of(path: Path) -> str | None:
    """Return the top-level module name if the file belongs to one of MODULES."""
    try:
        rel = path.relative_to(SRC_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if parts and parts[0] in MODULES:
        return parts[0]
    return None


def _is_cross_module_import(from_module: str, import_path: str) -> bool:
    """True if ``import_path`` references a sibling module other than ``from_module``."""
    for mod in MODULES:
        if mod == from_module:
            continue
        if import_path == f"jumlaos.{mod}" or import_path.startswith(f"jumlaos.{mod}."):
            return True
    return False


def check_file(path: Path, from_module: str) -> list[str]:
    """Return a list of violation messages for a single file."""
    violations: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_cross_module_import(from_module, alias.name):
                    violations.append(
                        f"{path}:{node.lineno}: "
                        f"'{from_module}' imports sibling module via 'import {alias.name}'"
                    )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and _is_cross_module_import(from_module, node.module)
        ):
            violations.append(
                f"{path}:{node.lineno}: "
                f"'{from_module}' imports sibling module via 'from {node.module} import ...'"
            )
    return violations


def main() -> int:
    all_violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        from_module = _module_of(py_file)
        if from_module is None:
            continue
        all_violations.extend(check_file(py_file, from_module))

    if all_violations:
        print("Module boundary violations found:\n")
        for v in all_violations:
            print(f"  {v}")
        print(f"\n{len(all_violations)} violation(s). Fix by routing through jumlaos.core.events.")
        return 1

    print("Module boundaries OK: no cross-module imports detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
