"""Testes do servidor HTTP local.

Tests for the local HTTP server.

A decisao de teste documentada em docs/: o servidor e criado com porta 0
(porta livre), subido em thread daemon e derrubado em try/finally
(shutdown + server_close), entao nenhum teste deixa porta aberta nem trava
a suite.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from pathlib import Path

import pytest

from helpdesk import servidor

DADOS = Path(__file__).resolve().parents[1] / "dados"


@pytest.fixture()
def http_server(banco_semeado):
    serv = servidor.criar_servidor(banco_semeado, DADOS, host="127.0.0.1", porta=0)
    thread = threading.Thread(target=serv.serve_forever, daemon=True)
    thread.start()
    try:
        yield serv
    finally:
        serv.shutdown()
        serv.server_close()
        thread.join(timeout=5)


def url(serv, caminho: str) -> str:
    return f"http://127.0.0.1:{servidor.porta_do_server(serv)}{caminho}"


def get(serv, caminho: str):
    with urllib.request.urlopen(url(serv, caminho), timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def test_raiz_responde_json(http_server) -> None:
    status, corpo = get(http_server, "/")
    assert status == 200
    assert corpo["servico"] == "helpdesk"
    assert corpo["total_chamados"] == 132
    assert corpo["abertos"] == 28
    assert sum(corpo["backlog_por_severidade"].values()) == 28


def test_fila_ordenada_por_severidade_e_tempo_de_espera(http_server) -> None:
    status, corpo = get(http_server, "/fila")
    assert status == 200
    fila_list = corpo["fila"]
    assert len(fila_list) == 28
    peso = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}
    chaves = [(peso[t["severidade"]], t["criado_em"]) for t in fila_list]
    assert chaves == sorted(chaves)


def test_chamado_por_id_e_404_bilingue(http_server) -> None:
    status, corpo = get(http_server, "/chamados/1")
    assert status == 200
    assert corpo["id"] == 1
    try:
        urllib.request.urlopen(url(http_server, "/chamados/99999"), timeout=10)
        raise AssertionError("deveria dar 404 / expected 404")
    except urllib.error.HTTPError as e:
        assert e.code == 404
        assert "ticket not found" in json.loads(e.read().decode("utf-8"))["erro"]


def test_inventario_e_relatorio_por_http(http_server) -> None:
    status, corpo = get(http_server, "/inventario")
    assert status == 200
    assert len(corpo["equipamentos"]) == 12
    total_chamados_ativos = sum(e["chamados"] for e in corpo["equipamentos"])
    assert total_chamados_ativos == 132

    status, corpo = get(http_server, "/relatorio")
    assert status == 200
    assert corpo["total"] == 132
    assert corpo["mttr_h"] > 0
    assert corpo["backlog"] == {"critica": 3, "alta": 7, "media": 8, "baixa": 10}


def test_post_cria_chamado(http_server) -> None:
    payload = json.dumps(
        {"titulo": "Chamado via HTTP", "severidade": "baixa", "solicitante": "Zeca Silva"}
    ).encode("utf-8")
    req = urllib.request.Request(
        url(http_server, "/chamados"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        assert r.status == 201
        novo_id = json.loads(r.read().decode("utf-8"))["id"]
    assert novo_id == 133
    status, corpo = get(http_server, f"/chamados/{novo_id}")
    assert status == 200
    assert corpo["titulo"] == "Chamado via HTTP"
    assert corpo["solicitante"] == "Zeca Silva"


def test_post_sem_titulo_da_400(http_server) -> None:
    payload = json.dumps({"descricao": "sem titulo"}).encode("utf-8")
    req = urllib.request.Request(
        url(http_server, "/chamados"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("deveria dar 400 / expected 400")
    except urllib.error.HTTPError as e:
        assert e.code == 400
        assert "titulo" in json.loads(e.read().decode("utf-8"))["erro"]


def test_post_severidade_invalida_da_400(http_server) -> None:
    payload = json.dumps({"titulo": "x", "severidade": "urgente"}).encode("utf-8")
    req = urllib.request.Request(
        url(http_server, "/chamados"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("deveria dar 400 / expected 400")
    except urllib.error.HTTPError as e:
        assert e.code == 400
        assert "invalid severity" in json.loads(e.read().decode("utf-8"))["erro"]


def test_rota_desconhecida_da_404(http_server) -> None:
    try:
        urllib.request.urlopen(url(http_server, "/nao-existe"), timeout=10)
        raise AssertionError("deveria dar 404 / expected 404")
    except urllib.error.HTTPError as e:
        assert e.code == 404
        assert "unknown route" in json.loads(e.read().decode("utf-8"))["erro"]
