"""Testes da camada SQLite e da populacao a partir do seed.

Tests for the SQLite layer and seed population.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpdesk import banco

DADOS = Path(__file__).resolve().parents[1] / "dados"


def test_garantir_banco_cria_e_popula(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        n_chamados = conex.execute("SELECT COUNT(*) AS n FROM chamados").fetchone()["n"]
        n_ativos = conex.execute("SELECT COUNT(*) AS n FROM equipamentos").fetchone()["n"]
        n_usuarios = conex.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
        assert n_chamados == 132
        assert n_ativos == 12
        assert n_usuarios == 10
    finally:
        conex.close()


def test_garantir_banco_idempotente(banco_semeado: Path) -> None:
    # segunda chamada nao duplica nada
    banco.garantir_banco(banco_semeado, DADOS)
    conex = banco.abrir(banco_semeado)
    try:
        n = conex.execute("SELECT COUNT(*) AS n FROM chamados").fetchone()["n"]
        assert n == 132
    finally:
        conex.close()


def test_popular_banco_nao_vazio_levanta(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        with pytest.raises(ValueError, match="already seeded"):
            banco.popular_do_seed(conex, DADOS)
    finally:
        conex.close()


def test_carregar_tickets_incorpora_usuario_e_ativo(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        tickets = banco.carregar_tickets(conex)
        assert len(tickets) == 132
        com_ativo = [t for t in tickets if t.ativo is not None]
        assert com_ativo
        assert all(t.solicitante is not None for t in tickets)
        assert all(t.solicitante.email.endswith("@empresaexemplo.com.br") for t in tickets)
        assert all(t.ativo.codigo == "SRV-MAIL-01" for t in com_ativo if t.ativo.codigo == "SRV-MAIL-01")
    finally:
        conex.close()


def test_buscar_ticket_inexistente_retorna_none(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        assert banco.buscar_ticket(conex, 99999) is None
    finally:
        conex.close()


def test_garantir_banco_sem_seed_levanta(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="seed file missing"):
        banco.garantir_banco(tmp_path / "vazio.sqlite", tmp_path)


def test_proximo_id_sequencial(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        assert banco.proximo_id(conex) == 133
    finally:
        conex.close()


def test_garantir_usuario_cria_e_reutiliza(banco_semeado: Path) -> None:
    conex = banco.abrir(banco_semeado)
    try:
        id1 = banco.garantir_usuario(conex, "Zeca Silva")
        id2 = banco.garantir_usuario(conex, "Zeca Silva")
        assert id1 == id2 == 11
    finally:
        conex.close()


def test_ultima_data_evento(banco_semeado: Path) -> None:
    import yaml

    bruto = yaml.safe_load((DADOS / "chamados-semente.yaml").read_text(encoding="utf-8"))
    datas = [c["criado_em"] for c in bruto["chamados"]]
    datas += [c[k] for c in bruto["chamados"] for k in ("primeira_resposta_em", "resolvido_em") if c.get(k)]
    conex = banco.abrir(banco_semeado)
    try:
        assert banco.ultima_data_evento(conex).strftime("%Y-%m-%dT%H:%M:%SZ") == max(datas)
    finally:
        conex.close()
