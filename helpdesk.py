"""Shim para rodar ``python -m helpdesk`` a partir da raiz do repositorio.

Shim so that ``python -m helpdesk`` works from the repository root without
installing the package: coloca ``src/`` no ``sys.path`` e delega ao pacote
real em ``src/helpdesk``.

The CLI itself, tests and the server use the package in ``src/helpdesk``;
this file only bridges the module path.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
_SRC = str(_RAIZ / "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if __name__ == "__main__":
    from helpdesk.cli import main

    raise SystemExit(main())
