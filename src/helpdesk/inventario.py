"""Inventario de equipamentos: registro, consulta e contagem de chamados.

Equipment inventory: registration, lookup and ticket counting.

O inventario e a entidade duradoura do helpdesk: equipamentos nao mudam
junto com o ciclo de vida dos chamados, e por isso os seeds ficam em
arquivos separados (ver ``docs/matriz-de-prioridade.md``).
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from .modelo import Equipamento


def adicionar(conex: sqlite3.Connection, eq: Equipamento) -> None:
    """Insere um equipamento no inventario.

    Insert one equipment record into the inventory.
    """
    if not eq.codigo or not eq.codigo.strip():
        raise ValueError("codigo do equipamento vazio / empty equipment code")
    conex.execute(
        "INSERT INTO equipamentos (codigo, tipo, marca, modelo, local, status) VALUES (?, ?, ?, ?, ?, ?)",
        (eq.codigo.strip(), eq.tipo, eq.marca, eq.modelo, eq.local, eq.status),
    )
    conex.commit()


def listar(conex: sqlite3.Connection, tipo: Optional[str] = None) -> list[Equipamento]:
    """Lista equipamentos, opcionalmente filtrados por tipo.

    List equipment, optionally filtered by type.
    """
    if tipo:
        linhas = conex.execute(
            "SELECT codigo, tipo, marca, modelo, local, status FROM equipamentos "
            "WHERE tipo = ? ORDER BY codigo",
            (tipo,),
        ).fetchall()
    else:
        linhas = conex.execute(
            "SELECT codigo, tipo, marca, modelo, local, status FROM equipamentos ORDER BY codigo"
        ).fetchall()
    return [
        Equipamento(
            codigo=l["codigo"],
            tipo=l["tipo"],
            marca=l["marca"],
            modelo=l["modelo"],
            local=l["local"],
            status=l["status"],
        )
        for l in linhas
    ]


def buscar(conex: sqlite3.Connection, codigo: str) -> Optional[Equipamento]:
    """Busca um equipamento por codigo; None se nao existe.

    Look up one equipment by code; None when absent.
    """
    linha = conex.execute(
        "SELECT codigo, tipo, marca, modelo, local, status FROM equipamentos WHERE codigo = ?",
        (codigo,),
    ).fetchone()
    if linha is None:
        return None
    return Equipamento(
        codigo=linha["codigo"],
        tipo=linha["tipo"],
        marca=linha["marca"],
        modelo=linha["modelo"],
        local=linha["local"],
        status=linha["status"],
    )


def marcar_inativo(conex: sqlite3.Connection, codigo: str) -> None:
    """Marca um equipamento como inativo (baixado do servico).

    Mark one equipment as inactive (retired from service).
    """
    alterado = conex.execute(
        "UPDATE equipamentos SET status = 'inativo' WHERE codigo = ?", (codigo,)
    )
    conex.commit()
    if alterado.rowcount == 0:
        raise LookupError(f"ativo nao encontrado / asset not found: {codigo}")


def contar_chamados(conex: sqlite3.Connection, codigo: Optional[str] = None) -> dict[str, int]:
    """Chamados por ativo (todos os status), por codigo.

    Tickets per asset code (any status).
    """
    if codigo:
        linhas = conex.execute(
            "SELECT ativo_codigo AS c, COUNT(*) AS n FROM chamados "
            "WHERE ativo_codigo = ? GROUP BY ativo_codigo",
            (codigo,),
        ).fetchall()
    else:
        linhas = conex.execute(
            "SELECT ativo_codigo AS c, COUNT(*) AS n FROM chamados "
            "WHERE ativo_codigo IS NOT NULL GROUP BY ativo_codigo"
        ).fetchall()
    return {l["c"]: int(l["n"]) for l in linhas}
