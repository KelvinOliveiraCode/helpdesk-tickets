"""Testes da fila: ordenacao por severidade e tempo de espera, atribuicao.

Tests for the queue: ordering by severity and waiting time, assignment.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from helpdesk import fila
from helpdesk.modelo import Ticket

BASE = datetime(2026, 1, 5, 8, 0, 0)


def t(id_: int, sev: str, dias: int, status: str = "aberto") -> Ticket:
    return Ticket(
        id=id_,
        titulo=f"t{id_}",
        descricao="d",
        severidade=sev,
        status=status,
        criado_em=BASE + timedelta(days=dias),
    )


def test_severidade_define_a_fila() -> None:
    f = fila.ordenar_fila([t(1, "baixa", 0), t(2, "critica", 5), t(3, "alta", 1)])
    # critica sai a frente mesmo tendo esperado menos que as outras
    assert [x.id for x in f] == [2, 3, 1]


def test_dentro_da_mesma_severidade_ganha_o_mais_antigo() -> None:
    f = fila.ordenar_fila([t(1, "media", 3), t(2, "media", 1)])
    assert [x.id for x in f] == [2, 1]


def test_empate_total_quebra_por_id() -> None:
    a = Ticket(id=9, titulo="a", descricao="d", severidade="baixa", status="aberto", criado_em=BASE)
    b = Ticket(id=3, titulo="b", descricao="d", severidade="baixa", status="aberto", criado_em=BASE)
    assert [x.id for x in fila.ordenar_fila([a, b])] == [3, 9]


def test_fila_aberta_ignora_resolvidos() -> None:
    f = fila.fila_aberta([t(1, "baixa", 0), t(2, "critica", 0, status="resolvido"), t(3, "media", 1)])
    assert [x.id for x in f] == [3, 1]


def test_posicao_na_fila() -> None:
    todos = [t(1, "media", 2), t(2, "critica", 0), t(3, "alta", 1)]
    assert fila.posicao_na_fila(todos[0], todos) == 3
    assert fila.posicao_na_fila(todos[1], todos) == 1
    assert fila.posicao_na_fila(t(9, "baixa", 0, status="resolvido"), todos) == -1


def test_atribuir_escolhe_menor_carga() -> None:
    agente = fila.atribuir_proximo(
        ["Time A", "Time B", "Time C"], {"Time A": 5, "Time B": 1, "Time C": 3}
    )
    assert agente == "Time B"


def test_atribuir_empate_por_ordem_alfabetica() -> None:
    agente = fila.atribuir_proximo(
        ["Time C", "Time A", "Time B"], {"Time A": 2, "Time B": 2, "Time C": 2}
    )
    assert agente == "Time A"


def test_atribuir_sem_agentes_levanta() -> None:
    with pytest.raises(ValueError, match="no agent available"):
        fila.atribuir_proximo([], {})
