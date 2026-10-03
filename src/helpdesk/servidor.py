"""Servidor HTTP local (http.server) por cima do banco do helpdesk.

Local HTTP server (http.server) on top of the helpdesk database.

Decisoes documentadas em ``docs/matriz-de-prioridade.md``:
- toda requisicao abre e fecha sua propria conexao SQLite (uma conexao
  aberta entre threads e pedido de problema);
- o servidor e criado SEM comecar a escutar, para os testes poderem
  subi-lo em thread daemon e derruba-lo em ``try/finally``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse

from . import __version__, banco, fila, inventario, modelo, relatorio

PORTA_PADRAO = 8471


def _criar_handler(caminho_banco: str | object, pasta_dados: str | object) -> type[BaseHTTPRequestHandler]:
    # A classe da handler captura os caminhos do banco pelo escopo.
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            # Acesso log silencioso: nao poluir o terminal do operador.
            pass

        def _json(self, status: int, payload: object) -> None:
            corpo = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _erro(self, status: int, mensagem: str) -> None:
            self._json(status, {"erro": mensagem})

        def _t_para_dict(self, t: modelo.Ticket) -> dict:
            return {
                "id": t.id,
                "titulo": t.titulo,
                "severidade": t.severidade,
                "status": t.status,
                "categoria": t.categoria,
                "ativo": t.ativo.codigo if t.ativo else None,
                "solicitante": t.solicitante.nome if t.solicitante else None,
                "agente": t.agente,
                "criado_em": t.criado_em.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "primeira_resposta_em": (
                    t.primeira_resposta_em.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if t.primeira_resposta_em
                    else None
                ),
                "resolvido_em": (
                    t.resolvido_em.strftime("%Y-%m-%dT%H:%M:%SZ") if t.resolvido_em else None
                ),
            }

        def do_GET(self) -> None:  # noqa: N802 - nome do http.server
            caminho = urlparse(self.path).path
            conex = banco.abrir(caminho_banco)
            try:
                if caminho == "/":
                    tickets = banco.carregar_tickets(conex)
                    abertos = [t for t in tickets if t.eh_aberto()]
                    backlog: dict[str, int] = {s: 0 for s in modelo.SEVERIDADES}
                    for t in abertos:
                        backlog[t.severidade] += 1
                    self._json(
                        200,
                        {
                            "servico": "helpdesk",
                            "versao": __version__,
                            "total_chamados": len(tickets),
                            "abertos": len(abertos),
                            "backlog_por_severidade": backlog,
                        },
                    )
                elif caminho == "/fila":
                    tickets = banco.carregar_tickets(conex)
                    self._json(
                        200,
                        {
                            "fila": [self._t_para_dict(t) for t in fila.fila_aberta(tickets)],
                        },
                    )
                elif caminho == "/inventario":
                    contagens = inventario.contar_chamados(conex)
                    self._json(
                        200,
                        {
                            "equipamentos": [
                                {
                                    "codigo": e.codigo,
                                    "tipo": e.tipo,
                                    "status": e.status,
                                    "chamados": contagens.get(e.codigo, 0),
                                }
                                for e in inventario.listar(conex)
                            ]
                        },
                    )
                elif caminho == "/relatorio":
                    tipos = relatorio.tipos_de_ativos(conex)
                    rel = relatorio.gerar(conex)
                    payload: dict[str, object] = {
                        "referencia": rel.referencia.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "total": rel.total,
                        "resolvidos": rel.resolvidos,
                        "sla_resposta": {
                            s: {
                                "avaliados": b.avaliados,
                                "dentro": b.dentro,
                                "estourados": b.estourados,
                                "percentual": b.percentual,
                            }
                            for s, b in rel.sla_resposta.items()
                        },
                        "sla_resolucao": {
                            s: {
                                "avaliados": b.avaliados,
                                "dentro": b.dentro,
                                "estourados": b.estourados,
                                "percentual": b.percentual,
                            }
                            for s, b in rel.sla_resolucao.items()
                        },
                        "backlog": {
                            s: rel.backlog_aberto[s] + rel.backlog_em_atendimento[s]
                            for s in modelo.SEVERIDADES
                        },
                        "mttr_h": rel.mttr_h,
                        "recorrentes": [
                            {"ativo": c, "tipo": tipos.get(c, "-"), "chamados": n}
                            for c, n in rel.recorrentes
                        ],
                    }
                    self._json(200, payload)
                elif caminho.startswith("/chamados/"):
                    try:
                        ticket_id = int(caminho.rsplit("/", 1)[-1])
                    except ValueError:
                        self._erro(400, "id de chamado invalido / invalid ticket id")
                        return
                    t = banco.buscar_ticket(conex, ticket_id)
                    if t is None:
                        self._erro(404, f"chamado nao encontrado / ticket not found: {ticket_id}")
                    else:
                        self._json(200, self._t_para_dict(t))
                else:
                    self._erro(404, "rota desconhecida / unknown route")
            finally:
                conex.close()

        def do_POST(self) -> None:  # noqa: N802 - nome do http.server
            caminho = urlparse(self.path).path
            if caminho != "/chamados":
                self._erro(405, "POST apenas em /chamados / POST only on /chamados")
                return
            try:
                tamanho = int(self.headers.get("Content-Length", "0"))
                bruto = self.rfile.read(tamanho) if tamanho else b""
                dados = json.loads(bruto.decode("utf-8")) if bruto else {}
            except (ValueError, UnicodeDecodeError):
                self._erro(400, "corpo da requisicao invalido / invalid request body")
                return
            if not isinstance(dados, dict) or not str(dados.get("titulo", "")).strip():
                self._erro(400, "campo 'titulo' e obrigatorio / 'titulo' is required")
                return
            severidade = str(dados.get("severidade", "media"))
            if severidade not in modelo.SEVERIDADES:
                self._erro(
                    400,
                    "severidade invalida / invalid severity (esperado: critica, alta, media, baixa)",
                )
                return
            ativo = dados.get("ativo")
            conex = banco.abrir(caminho_banco)
            try:
                if ativo is not None and inventario.buscar(conex, str(ativo)) is None:
                    self._erro(404, f"ativo nao encontrado / asset not found: {ativo}")
                    return
                solicitante = str(dados.get("solicitante", "Anonimo"))
                solicitante_id = banco.garantir_usuario(conex, solicitante)
                criado_em = str(dados.get("criado_em") or datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                agora = modelo.para_dt(criado_em)
                ticket_id = banco.abrir_chamado(
                    conex,
                    titulo=str(dados["titulo"]).strip(),
                    descricao=str(dados.get("descricao", "")).strip(),
                    severidade=severidade,
                    categoria=dados.get("categoria"),
                    solicitante_id=solicitante_id,
                    ativo_codigo=str(ativo) if ativo is not None else None,
                    criado_em=agora,
                )
                self._json(201, {"id": ticket_id, "status": "aberto"})
            finally:
                conex.close()

    return Handler


def criar_servidor(
    caminho_banco: str | object,
    pasta_dados: str | object,
    host: str = "127.0.0.1",
    porta: int = PORTA_PADRAO,
) -> ThreadingHTTPServer:
    """Cria o servidor SEM comecar a escutar.

    Create the server without starting to listen, so tests can start it in a
    daemon thread and shut it down in ``try/finally``.
    """
    banco.garantir_banco(caminho_banco, pasta_dados)
    handler = _criar_handler(caminho_banco, pasta_dados)
    server = ThreadingHTTPServer((host, porta), handler)
    server.daemon_threads = True
    return server


def porta_do_server(server: ThreadingHTTPServer) -> int:
    """Porta real em escuta (necessario quando a porta foi 0).

    The actual listening port (needed when port 0 was requested).
    """
    return int(server.server_address[1])
