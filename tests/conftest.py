"""Fixtures compartilhadas dos testes.

Shared fixtures for the test suite.

Toda fixture de banco usa ``tmp_path`` (arquivo temporario) e nunca deixa
conexao aberta: quem abre fecha no ``finally``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpdesk import banco

DADOS = Path(__file__).resolve().parents[1] / "dados"


@pytest.fixture()
def banco_semeado(tmp_path: Path) -> Path:
    """Banco SQLite temporario ja populado com o seed de dados/.

    A temporary SQLite database already populated from the dados/ seed.
    """
    caminho = tmp_path / "hd.sqlite"
    banco.garantir_banco(caminho, DADOS)
    return caminho
