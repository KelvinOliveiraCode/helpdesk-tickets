"""Prazos de SLA por severidade, medidos em dois relogios separados.

SLA deadlines per severity, measured on two separate clocks: time to first
response and time to resolution.

A decisao de usar 4x o prazo de resposta como prazo de resolucao esta
documentada em ``docs/matriz-de-prioridade.md``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .modelo import SEVERIDADES, Ticket

# Prazo em horas para a PRIMEIRA RESPOSTA, por severidade.
PRORROS_RESPOSTA_H = {
    "critica": 1.0,
    "alta": 4.0,
    "media": 8.0,
    "baixa": 24.0,
}

# Prazo em horas para RESOLUCAO: 4x o prazo de resposta.
PRORROS_RESOLUCAO_H = {
    "critica": 4.0,
    "alta": 16.0,
    "media": 32.0,
    "baixa": 96.0,
}


def _validar(severidade: str) -> None:
    # A validacao mora aqui, nao no chamador.
    if severidade not in SEVERIDADES:
        raise ValueError(
            f"severidade invalida: {severidade} / invalid severity: {severidade}"
        )


def prazo_resposta_h(severidade: str) -> float:
    """Prazo (horas) da primeira resposta para a severidade dada.

    First-response deadline (hours) for the given severity.
    """
    _validar(severidade)
    return PRORROS_RESPOSTA_H[severidade]


def prazo_resolucao_h(severidade: str) -> float:
    """Prazo (horas) de resolucao para a severidade dada.

    Resolution deadline (hours) for the given severity.
    """
    _validar(severidade)
    return PRORROS_RESOLUCAO_H[severidade]


def tempo_resposta(t: Ticket) -> timedelta | None:
    """Tempo da abertura a primeira resposta; None se ainda sem resposta.

    Time from creation to first answer; None when unanswered.
    """
    if t.primeira_resposta_em is None:
        return None
    return t.primeira_resposta_em - t.criado_em


def tempo_resolucao(t: Ticket) -> timedelta | None:
    """Tempo da abertura a resolucao; None se ainda aberto.

    Time from creation to resolution; None while open.
    """
    if t.resolvido_em is None:
        return None
    return t.resolvido_em - t.criado_em


def violou_resposta(t: Ticket) -> bool:
    """True se a primeira resposta chegou depois do prazo da severidade.

    True if the first answer arrived after the severity deadline.
    """
    tr = tempo_resposta(t)
    if tr is None:
        return False
    return tr > timedelta(hours=prazo_resposta_h(t.severidade))


def violou_resolucao(t: Ticket) -> bool:
    """True se a resolucao veio depois do prazo da severidade.

    True if the resolution came after the severity deadline.
    """
    tr = tempo_resolucao(t)
    if tr is None:
        return False
    return tr > timedelta(hours=prazo_resolucao_h(t.severidade))


def resposta_em_atraso(t: Ticket, agora: datetime) -> bool:
    """True se aberto, sem resposta e ja fora do prazo de resposta.

    True when open without an answer and already past the response deadline.
    """
    if not t.eh_aberto() or t.primeira_resposta_em is not None:
        return False
    return t.tempo_espera(agora) > timedelta(hours=prazo_resposta_h(t.severidade))


def resolucao_em_atraso(t: Ticket, agora: datetime) -> bool:
    """True se aberto e ja fora do prazo de resolucao.

    True when open and already past the resolution deadline.
    """
    if not t.eh_aberto():
        return False
    return t.tempo_espera(agora) > timedelta(hours=prazo_resolucao_h(t.severidade))
