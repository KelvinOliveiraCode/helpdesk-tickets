"""Relatorio de desempenho: SLA atingido, backlog, MTTR e ativos recorrentes.

Performance report: SLA attainment, backlog, MTTR and recurring assets.

A data de referencia nao e o relogio do sistema: por padrao e o ultimo
evento presente no banco. Assim a mesma base de dados produz sempre o
mesmo relatorio (ver ``docs/matriz-de-prioridade.md``).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import banco, sla
from .modelo import SEVERIDADES, Ticket

TOP_PADRAO = 5


@dataclass
class BlocoSla:
    """Contagem de um relogio de SLA para uma severidade.

    One SLA clock's counts for a severity.
    """

    avaliados: int = 0
    dentro: int = 0
    estourados: int = 0

    @property
    def percentual(self) -> Optional[float]:
        """Percentual de SLA atingido; None sem base para calcular.

        SLA attainment percentage; None when there is no base.
        """
        if self.avaliados == 0:
            return None
        return round(100.0 * self.dentro / self.avaliados, 1)


@dataclass
class Relatorio:
    """Resultado completo do desempenho do helpdesk.

    The full helpdesk performance result.
    """

    referencia: datetime
    total: int
    resolvidos: int
    sla_resposta: dict[str, BlocoSla] = field(default_factory=dict)
    sla_resolucao: dict[str, BlocoSla] = field(default_factory=dict)
    backlog_aberto: dict[str, int] = field(default_factory=dict)
    backlog_em_atendimento: dict[str, int] = field(default_factory=dict)
    backlog_estourado: int = 0
    mttr_h: float = 0.0
    recorrentes: list[tuple[str, int]] = field(default_factory=list)


def gerar(conex: sqlite3.Connection, referencia: Optional[datetime] = None, top: int = TOP_PADRAO) -> Relatorio:
    """Calcula o relatorio a partir do banco.

    Compute the report from the database.

    ``referencia`` None usa o ultimo evento do banco; com banco vazio,
    levanta ``ValueError``.
    """
    tickets = banco.carregar_tickets(conex)
    if not tickets:
        raise ValueError("banco vazio; nada para reportar / empty database; nothing to report")
    if referencia is None:
        referencia = banco.ultima_data_evento(conex)
        if referencia is None:
            raise ValueError("banco vazio; nada para reportar / empty database; nothing to report")

    resp = {s: BlocoSla() for s in SEVERIDADES}
    res = {s: BlocoSla() for s in SEVERIDADES}
    aberto = {s: 0 for s in SEVERIDADES}
    em_atend = {s: 0 for s in SEVERIDADES}
    estourado_aberto = 0
    resolvidos: list[Ticket] = []

    for t in tickets:
        if t.primeira_resposta_em is not None:
            bloco = resp[t.severidade]
            bloco.avaliados += 1
            if sla.violou_resposta(t):
                bloco.estourados += 1
            else:
                bloco.dentro += 1
        if t.resolvido_em is not None:
            bloco = res[t.severidade]
            bloco.avaliados += 1
            if sla.violou_resolucao(t):
                bloco.estourados += 1
            else:
                bloco.dentro += 1
            resolvidos.append(t)
        if t.status == "aberto":
            aberto[t.severidade] += 1
        elif t.status == "em_atendimento":
            em_atend[t.severidade] += 1
        if sla.resolucao_em_atraso(t, referencia):
            estourado_aberto += 1

    duracoes = [t.duracao_resolucao() for t in resolvidos]
    horas = [d.total_seconds() / 3600.0 for d in duracoes if d is not None]
    mttr = round(sum(horas) / len(horas), 2) if horas else 0.0

    contagem: dict[str, int] = {}
    for t in tickets:
        if t.ativo is not None:
            contagem[t.ativo.codigo] = contagem.get(t.ativo.codigo, 0) + 1
    # empate decide por codigo, para o top ser estavel
    recorrentes = sorted(contagem.items(), key=lambda item: (-item[1], item[0]))[:top]

    return Relatorio(
        referencia=referencia,
        total=len(tickets),
        resolvidos=len(resolvidos),
        sla_resposta=resp,
        sla_resolucao=res,
        backlog_aberto=aberto,
        backlog_em_atendimento=em_atend,
        backlog_estourado=estourado_aberto,
        mttr_h=mttr,
        recorrentes=recorrentes,
    )


def _linha_percentual(bloco: BlocoSla) -> str:
    if bloco.percentual is None:
        return "n/d"
    return f"{bloco.percentual:.1f}"


def markdown(rel: Relatorio, tipos_ativo: dict[str, str]) -> str:
    """Monta o relatorio em Markdown (PT-BR, texto plano e deterministico).

    Build the report as Markdown (PT-BR, plain and deterministic text).
    """
    linhas: list[str] = []
    linhas.append("# Relatorio de desempenho - helpdesk")
    linhas.append("")
    linhas.append(f"- Data de referencia: {rel.referencia.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    linhas.append(f"- Chamados no banco: {rel.total}")
    linhas.append(f"- Resolvidos: {rel.resolvidos}")
    linhas.append(f"- Abertos na fila (aberto + em atendimento): {rel.total - rel.resolvidos}")
    linhas.append("")
    linhas.append("## SLA de resposta (tempo ate a primeira resposta)")
    linhas.append("")
    linhas.append("| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |")
    linhas.append("|---|---:|---:|---:|---:|")
    for s in SEVERIDADES:
        b = rel.sla_resposta[s]
        linhas.append(
            f"| {s} | {b.avaliados} | {b.dentro} | {b.estourados} | {_linha_percentual(b)} |"
        )
    linhas.append("")
    linhas.append("## SLA de resolucao (tempo da abertura a resolucao)")
    linhas.append("")
    linhas.append("| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |")
    linhas.append("|---|---:|---:|---:|---:|")
    for s in SEVERIDADES:
        b = rel.sla_resolucao[s]
        linhas.append(
            f"| {s} | {b.avaliados} | {b.dentro} | {b.estourados} | {_linha_percentual(b)} |"
        )
    linhas.append("")
    linhas.append("## Backlog por severidade")
    linhas.append("")
    linhas.append("| Severidade | Aberto | Em atendimento | Total |")
    linhas.append("|---|---:|---:|---:|")
    for s in SEVERIDADES:
        total = rel.backlog_aberto[s] + rel.backlog_em_atendimento[s]
        linhas.append(f"| {s} | {rel.backlog_aberto[s]} | {rel.backlog_em_atendimento[s]} | {total} |")
    linhas.append(f"| Total | {sum(rel.backlog_aberto.values())} | {sum(rel.backlog_em_atendimento.values())} | {rel.total - rel.resolvidos} |")
    linhas.append("")
    linhas.append(f"- Abertos ja estourados no prazo de resolucao (na data de referencia): {rel.backlog_estourado}")
    linhas.append("")
    linhas.append("## MTTR (tempo medio de resolucao)")
    linhas.append("")
    linhas.append(f"- MTTR: {rel.mttr_h:.2f} h, calculado sobre {rel.resolvidos} chamados resolvidos.")
    linhas.append("")
    linhas.append("## Chamados mais recorrentes por ativo")
    linhas.append("")
    if rel.recorrentes:
        linhas.append("| Ativo | Tipo | Chamados |")
        linhas.append("|---|---|---:|")
        for codigo, n in rel.recorrentes:
            tipo = tipos_ativo.get(codigo, "-")
            linhas.append(f"| {codigo} | {tipo} | {n} |")
    else:
        linhas.append("- Nenhum chamado referencia um ativo.")
    linhas.append("")
    return "\n".join(linhas) + "\n"


def tipos_de_ativos(conex: sqlite3.Connection) -> dict[str, str]:
    """Tipo de cada ativo, por codigo (para decorar o top de recorrentes).

    Type per asset code (used to decorate the recurring-assets top).
    """
    linhas = conex.execute("SELECT codigo, tipo FROM equipamentos").fetchall()
    return {l["codigo"]: l["tipo"] for l in linhas}
