"""Testes do relatorio de desempenho, conferidos contra o seed plantado.

Tests for the performance report, checked against the planted seed so that
the report provably matches the data in dados/.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from helpdesk import banco, relatorio
from helpdesk.modelo import para_dt

DADOS = Path(__file__).resolve().parents[1] / "dados"

PRORRO_RESPOSTA_H = {"critica": 1.0, "alta": 4.0, "media": 8.0, "baixa": 24.0}
PRORRO_RESOLUCAO_H = {k: 4.0 * v for k, v in PRORRO_RESPOSTA_H.items()}


def seed_chamados() -> list[dict]:
    bruto = yaml.safe_load((DADOS / "chamados-semente.yaml").read_text(encoding="utf-8"))
    return bruto["chamados"]


def gerar(banco_semeado: Path) -> relatorio.Relatorio:
    conex = banco.abrir(banco_semeado)
    try:
        return relatorio.gerar(conex)
    finally:
        conex.close()


def test_total_e_resolvidos_batem_com_seed(banco_semeado: Path) -> None:
    chs = seed_chamados()
    rel = gerar(banco_semeado)
    assert rel.total == 132
    assert rel.resolvidos == 104
    assert rel.total - rel.resolvidos == 28  # backlog em cada severidade


def test_contagem_exata_por_severidade(banco_semeado: Path) -> None:
    chs = seed_chamados()
    esp = dict(Counter(c["severidade"] for c in chs))
    rel = gerar(banco_semeado)
    for s in ("critica", "alta", "media", "baixa"):
        respondidos = sum(
            1 for c in chs if c["severidade"] == s and c.get("primeira_resposta_em")
        )
        abertos_sem_resp = sum(
            1 for c in chs if c["severidade"] == s and not c.get("primeira_resposta_em")
        )
        # contagem exata do seed: respondidos + abertos sem resposta = total
        assert rel.sla_resposta[s].avaliados == respondidos
        assert respondidos + abertos_sem_resp == esp[s]
    # total plantado: 132 chamados, 120 com resposta, 12 sem
    assert sum(b.avaliados for b in rel.sla_resposta.values()) == 120
    assert sum(esp.values()) == 132


def test_backlog_por_severidade_bate_com_seed(banco_semeado: Path) -> None:
    chs = seed_chamados()
    rel = gerar(banco_semeado)
    for s in ("critica", "alta", "media", "baixa"):
        assert rel.backlog_aberto[s] == sum(
            1 for c in chs if c["status"] == "aberto" and c["severidade"] == s
        )
        assert rel.backlog_em_atendimento[s] == sum(
            1 for c in chs if c["status"] == "em_atendimento" and c["severidade"] == s
        )
    # a spec exige backlog aberto em cada severidade
    for s in ("critica", "alta", "media", "baixa"):
        assert rel.backlog_aberto[s] + rel.backlog_em_atendimento[s] > 0


def test_sla_resposta_bate_com_seed(banco_semeado: Path) -> None:
    chs = seed_chamados()
    rel = gerar(banco_semeado)
    for s in ("critica", "alta", "media", "baixa"):
        avaliados = 0
        estourados = 0
        for c in chs:
            if c["severidade"] == s and c.get("primeira_resposta_em"):
                avaliados += 1
                gasto_h = (
                    para_dt(c["primeira_resposta_em"]) - para_dt(c["criado_em"])
                ).total_seconds() / 3600.0
                estourados += 1 if gasto_h > PRORRO_RESPOSTA_H[s] else 0
        b = rel.sla_resposta[s]
        assert b.avaliados == avaliados
        assert b.estourados == estourados
        assert b.dentro == avaliados - estourados
    # a spec exige chamados que estouram o SLA de resposta
    assert sum(b.estourados for b in rel.sla_resposta.values()) > 0


def test_sla_resolucao_bate_com_seed(banco_semeado: Path) -> None:
    chs = seed_chamados()
    rel = gerar(banco_semeado)
    for s in ("critica", "alta", "media", "baixa"):
        avaliados = 0
        estourados = 0
        for c in chs:
            if c["severidade"] == s and c.get("resolvido_em"):
                avaliados += 1
                gasto_h = (
                    para_dt(c["resolvido_em"]) - para_dt(c["criado_em"])
                ).total_seconds() / 3600.0
                estourados += 1 if gasto_h > PRORRO_RESOLUCAO_H[s] else 0
        b = rel.sla_resolucao[s]
        assert b.avaliados == avaliados
        assert b.estourados == estourados
    # a spec exige chamados que estouram o SLA de resolucao
    assert sum(b.estourados for b in rel.sla_resolucao.values()) > 0


def test_mttr_bate_com_seed(banco_semeado: Path) -> None:
    chs = seed_chamados()
    res = [c for c in chs if c.get("resolvido_em")]
    horas = [
        (para_dt(c["resolvido_em"]) - para_dt(c["criado_em"])).total_seconds() / 3600.0
        for c in res
    ]
    esperado = round(sum(horas) / len(horas), 2)
    rel = gerar(banco_semeado)
    assert rel.mttr_h == esperado
    assert len(res) == 104


def test_ativos_recorrentes_topo_bate_com_seed(banco_semeado: Path) -> None:
    esp = Counter(c["ativo"] for c in seed_chamados())
    rel = gerar(banco_semeado)
    assert rel.recorrentes[0] == (esp.most_common(1)[0][0], esp.most_common(1)[0][1])
    # os dois ativos claramente recorrentes sao os primeiros do top
    assert rel.recorrentes[0][0] == "SRV-MAIL-01"
    assert rel.recorrentes[1][0] == "SW-CORE-01"
    assert rel.recorrentes[0][1] > rel.recorrentes[2][1]


def test_markdown_contem_as_secoes_e_o_mttr(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        rel = relatorio.gerar(conex)
        tipos = relatorio.tipos_de_ativos(conex)
    finally:
        conex.close()
    texto = relatorio.markdown(rel, tipos)
    assert "Relatorio de desempenho - helpdesk" in texto
    for secao in (
        "## SLA de resposta",
        "## SLA de resolucao",
        "## Backlog por severidade",
        "## MTTR",
        "## Chamados mais recorrentes por ativo",
    ):
        assert secao in texto
    assert f"{rel.mttr_h:.2f}" in texto
    assert "SRV-MAIL-01" in texto


def test_relatorio_banco_vazio_levanta(tmp_path: Path) -> None:
    caminho = tmp_path / "vazio.sqlite"
    banco.criar(caminho)
    conex = banco.abrir(caminho)
    try:
        with pytest.raises(ValueError, match="empty database"):
            relatorio.gerar(conex)
    finally:
        conex.close()
