"""Testes dos modelos de dados: Ticket, Usuario, Equipamento.

Tests for the data models: Ticket, Usuario, Equipamento.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from helpdesk.modelo import (
    ABERTOS,
    SEVERIDADES,
    STATUS,
    Ticket,
    Usuario,
    para_dt,
    para_iso,
)

CRIADO = datetime(2026, 1, 5, 8, 0, 0)


def ticket(**kw) -> Ticket:
    # ticket minimo valido; o teste so troca o que importa
    base = dict(id=1, titulo="T", descricao="D", severidade="media", status="aberto", criado_em=CRIADO)
    base.update(kw)
    return Ticket(**base)


def test_para_dt_com_z_e_para_iso_simetricos() -> None:
    dt = para_dt("2026-01-05T08:12:00Z")
    assert dt == datetime(2026, 1, 5, 8, 12, 0)
    assert dt.tzinfo is None
    assert para_iso(dt) == "2026-01-05T08:12:00Z"


def test_para_dt_data_invalida_levanta() -> None:
    with pytest.raises(ValueError):
        para_dt("05/01/2026 08:00")


def test_ticket_severidade_invalida_levanta() -> None:
    with pytest.raises(ValueError, match="invalid severity"):
        ticket(severidade="urgente")


def test_ticket_status_invalido_levanta() -> None:
    with pytest.raises(ValueError, match="invalid status"):
        ticket(status="fechado_x")


def test_resposta_antes_da_abertura_levanta() -> None:
    with pytest.raises(ValueError, match="before creation"):
        ticket(primeira_resposta_em=CRIADO - timedelta(minutes=5))


def test_tempo_espera_e_duracao() -> None:
    t = ticket(resolvido_em=CRIADO + timedelta(hours=3))
    assert t.tempo_espera(CRIADO + timedelta(hours=1)) == timedelta(hours=1)
    assert t.duracao_resolucao() == timedelta(hours=3)
    assert ticket().duracao_resolucao() is None


def test_eh_aberto_somente_para_status_da_fila() -> None:
    assert ticket().eh_aberto()
    assert ticket(status="em_atendimento").eh_aberto()
    assert not ticket(status="resolvido").eh_aberto()
    assert set(ABERTOS) == {"aberto", "em_atendimento"}
    assert set(SEVERIDADES) == {"critica", "alta", "media", "baixa"}
    assert set(STATUS) == {"aberto", "em_atendimento", "resolvido", "fechado"}


def test_usuario_criar_email_deterministico() -> None:
    u = Usuario.criar("Ana Duarte", 42, "Financeiro")
    assert u.email == "ana.duarte@empresaexemplo.com.br"
    assert u.departamento == "Financeiro"
    # mesmo nome, id diferente: o e-mail e funcao so do nome
    assert Usuario.criar("Ana Duarte", 7).email == u.email
