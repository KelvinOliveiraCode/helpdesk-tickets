"""Ordenacao da fila de chamados e atribuicao a agentes.

Ticket queue ordering and deterministic assignment to agents.

A fila respeita duas regras, nesta ordem:
1. severidade (critica primeiro);
2. tempo de espera (mais antigo primeiro).
The queue honors two rules, in this order:
1. severity (critical first);
2. waiting time (oldest first).
"""

from __future__ import annotations

from typing import Iterable, Mapping

from .modelo import ABERTOS, Ticket

# Menor peso sai primeiro: critica e sempre a frente.
_PESO_SEVERIDADE = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}


def _chave(t: Ticket) -> tuple[int, str, int]:
    # criado_em e sempre identico no formato ISO, entao compara como string
    # a mesma coisa que compara como datetime, sem trabalho extra.
    return (_PESO_SEVERIDADE[t.severidade], t.criado_em.strftime("%Y-%m-%dT%H:%M:%SZ"), t.id)


def ordenar_fila(chamados: Iterable[Ticket]) -> list[Ticket]:
    """Ordena por severidade e depois por tempo de espera (mais antigo primeiro).

    Sort by severity, then by waiting time (oldest first).
    """
    return sorted(chamados, key=_chave)


def fila_aberta(chamados: Iterable[Ticket]) -> list[Ticket]:
    """So os chamados que ocupam a fila, ja ordenados.

    Only the tickets still in the queue, already ordered.
    """
    return ordenar_fila([t for t in chamados if t.status in ABERTOS])


def posicao_na_fila(chamado: Ticket, chamados: Iterable[Ticket]) -> int:
    """Posicao (1-based) do chamado na fila aberta; -1 se nao esta nela.

    1-based position of the ticket in the open queue; -1 when not queued.
    """
    for i, t in enumerate(fila_aberta(chamados)):
        if t.id == chamado.id:
            return i + 1
    return -1


def atribuir_proximo(
    agentes: Iterable[str],
    cargas: Mapping[str, int],
) -> str:
    """Escolhe o agente com menos chamados abertos; empate por ordem alfabetica.

    Pick the agent with the fewest open tickets; ties break alphabetically,
    which keeps the assignment deterministic.
    """
    if not agentes:
        raise ValueError("nenhum agente disponivel / no agent available")
    lista = list(agentes)
    return min(lista, key=lambda a: (cargas.get(a, 0), a))
