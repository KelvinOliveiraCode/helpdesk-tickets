"""Testes do SLA: prazos por severidade, relogios de resposta e resolucao.

Tests for the SLA: deadlines per severity, response and resolution clocks.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from helpdesk import sla
from helpdesk.modelo import Ticket

CRIADO = datetime(2026, 1, 5, 8, 0, 0)


def t(sev: str, status: str = "resolvido", resposta=None, resolucao=None) -> Ticket:
    return Ticket(
        id=1,
        titulo="t",
        descricao="d",
        severidade=sev,
        status=status,
        criado_em=CRIADO,
        primeira_resposta_em=resposta,
        resolvido_em=resolucao,
    )


def test_prazos_resposta_por_severidade() -> None:
    # os quatro prazos da spec, sem erro
    assert sla.prazo_resposta_h("critica") == 1.0
    assert sla.prazo_resposta_h("alta") == 4.0
    assert sla.prazo_resposta_h("media") == 8.0
    assert sla.prazo_resposta_h("baixa") == 24.0


def test_prazo_resolucao_e_quatro_vezes_o_de_resposta() -> None:
    for s in ("critica", "alta", "media", "baixa"):
        assert sla.prazo_resolucao_h(s) == 4 * sla.prazo_resposta_h(s)


def test_severidade_invalida_levanta() -> None:
    with pytest.raises(ValueError, match="invalid severity"):
        sla.prazo_resposta_h("manha")
    with pytest.raises(ValueError, match="invalid severity"):
        sla.prazo_resolucao_h("manha")


def test_violou_resposta_dentro_do_prazo() -> None:
    assert not sla.violou_resposta(t("media", resposta=CRIADO + timedelta(hours=2)))


def test_violou_resposta_estourado() -> None:
    assert sla.violou_resposta(t("media", resposta=CRIADO + timedelta(hours=9)))


def test_violou_resposta_sem_resposta_e_false() -> None:
    # chamado aberto ainda nao estourou relogio nenhum para o relogio de resposta
    assert not sla.violou_resposta(t("critica", status="aberto"))


def test_violou_resolucao_dentro_e_estourado() -> None:
    dentro = t("critica", resolucao=CRIADO + timedelta(hours=3))
    fora = t("critica", resolucao=CRIADO + timedelta(hours=5))
    assert not sla.violou_resolucao(dentro)
    assert sla.violou_resolucao(fora)
    assert not sla.violou_resolucao(t("baixa", status="aberto"))


def test_relogios_sao_independentes() -> None:
    # resposta rapidissima e resolucao demorada: so o relogio de resolucao estoura
    t2 = t("media", resposta=CRIADO + timedelta(minutes=30), resolucao=CRIADO + timedelta(hours=40))
    assert not sla.violou_resposta(t2)
    assert sla.violou_resolucao(t2)


def test_resposta_em_atraso_somente_para_aberto_sem_resposta() -> None:
    agora = CRIADO + timedelta(hours=2)
    assert sla.resposta_em_atraso(t("critica", status="aberto"), agora)
    assert not sla.resposta_em_atraso(
        t("critica", status="aberto", resposta=CRIADO + timedelta(minutes=30)), agora
    )
    assert not sla.resposta_em_atraso(t("critica"), agora)


def test_resolucao_em_atraso_para_aberto_ja_vencido() -> None:
    agora = CRIADO + timedelta(days=2)
    assert sla.resolucao_em_atraso(t("media", status="aberto"), agora)
    # baixa tem 96h de prazo: 2 dias ainda nao estouram
    assert not sla.resolucao_em_atraso(t("baixa", status="aberto"), agora)
