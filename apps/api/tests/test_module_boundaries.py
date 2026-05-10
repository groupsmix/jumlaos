"""F05: verify that the module-boundary checker itself works.

Also acts as a gate: if any real cross-module imports exist in the codebase,
this test will fail.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_no_cross_module_imports() -> None:
    """Run the boundary checker and assert zero violations."""
    script = Path(__file__).resolve().parent.parent / "scripts" / "check_module_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(script.parent.parent),
    )
    assert result.returncode == 0, (
        f"Module boundary violations detected:\n{result.stdout}\n{result.stderr}"
    )
