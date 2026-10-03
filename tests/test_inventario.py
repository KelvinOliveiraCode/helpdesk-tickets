"""Testes do inventario de equipamentos.

Tests for the equipment inventory.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from helpdesk import inventario
from helpdesk.modelo import Equipamento

SCHEMA_MINIMO = """
CREATE TABLE equipamentos (
    codigo TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    local TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativo'
);
CREATE TABLE chamados (
    id INTEGER PRIMARY KEY,
    ativo_codigo TEXT
);
"""


def conexao(tmp_path: Path) -> sqlite3.Connection:
    # arquivo temporario; o teste fecha a conexao no finally
    c = sqlite3.connect(str(tmp_path / "inv.sqlite"))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA_MINIMO)
    c.commit()
    return c


def test_adicionar_e_listar(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        inventario.adicionar(c, Equipamento("NB-99", "Laptop", "Prisma", "T14", "Financeiro"))
        eqs = inventario.listar(c)
        assert len(eqs) == 1
        assert eqs[0].codigo == "NB-99"
        assert eqs[0].status == "ativo"
    finally:
        c.close()


def test_buscar_inexistente_retorna_none(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        assert inventario.buscar(c, "NAO-EXISTE") is None
    finally:
        c.close()


def test_codigo_vazio_levanta(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        with pytest.raises(ValueError, match="empty equipment code"):
            inventario.adicionar(c, Equipamento("  ", "PC", "X", "Y", "Z"))
    finally:
        c.close()


def test_lista_filtrada_por_tipo(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        inventario.adicionar(c, Equipamento("NB-1", "Laptop", "Prisma", "T14", "A"))
        inventario.adicionar(c, Equipamento("SRV-1", "Servidor", "Vertex", "R7", "B"))
        assert [e.codigo for e in inventario.listar(c, tipo="Laptop")] == ["NB-1"]
        assert len(inventario.listar(c)) == 2
    finally:
        c.close()


def test_marcar_inativo(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        inventario.adicionar(c, Equipamento("MON-1", "Monitor", "Delta", "P24", "C"))
        inventario.marcar_inativo(c, "MON-1")
        assert inventario.buscar(c, "MON-1").status == "inativo"
        with pytest.raises(LookupError, match="asset not found"):
            inventario.marcar_inativo(c, "MON-2")
    finally:
        c.close()


def test_contar_chamados_por_ativo(tmp_path: Path) -> None:
    c = conexao(tmp_path)
    try:
        for i in range(1, 4):
            c.execute("INSERT INTO chamados (id, ativo_codigo) VALUES (?, ?)", (i, "SRV-1"))
        c.execute("INSERT INTO chamados (id, ativo_codigo) VALUES (?, ?)", (4, "NB-1"))
        c.execute("INSERT INTO chamados (id, ativo_codigo) VALUES (?, ?)", (5, None))
        c.commit()
        assert inventario.contar_chamados(c) == {"SRV-1": 3, "NB-1": 1}
        assert inventario.contar_chamados(c, "SRV-1") == {"SRV-1": 3}
    finally:
        c.close()
