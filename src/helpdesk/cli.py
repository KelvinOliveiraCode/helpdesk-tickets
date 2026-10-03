"""Interface de linha de comando do helpdesk.

Command-line interface for the helpdesk.

Codigos de saida: 0 sucesso, 1 erro de dominio (mensagem bilingue no
stderr), 2 erro de uso (argumentos invalidos).
Exit codes: 0 success, 1 domain error (bilingual message on stderr),
2 usage error (invalid arguments).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from . import __version__, banco, fila, inventario, modelo, relatorio, servidor


class ErroUso(Exception):
    """Erro de uso de argumentos (saida 2). / Usage error (exit 2)."""


def _agora_utc() -> datetime:
    # UTC naive, alinhado com a convencao do modelo.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_data(valor: str) -> datetime:
    try:
        return modelo.para_dt(valor)
    except ValueError:
        raise ErroUso(f"data invalida / invalid timestamp: {valor}") from None


def _carregar_catalogo(pasta_dados: str) -> Optional[dict]:
    """Le o catalogo de servicos; None quando o arquivo nao existe.

    Load the service catalog; None when the file does not exist.
    """
    caminho = Path(pasta_dados) / "catalogo-servicos.yaml"
    if not caminho.exists():
        return None
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if not isinstance(bruto, dict):
        raise ErroUso("catalogo de servicos invalido / invalid service catalog")
    return bruto


def _equipes_do_catalogo(pasta_dados: str) -> list[str]:
    catalogos = _carregar_catalogo(pasta_dados)
    equipes = (catalogos or {}).get("equipes") or []
    return [str(e) for e in equipes] or ["Time A"]


# ---------------------------------------------------------------------------
# comandos
# ---------------------------------------------------------------------------


def cmd_abrir(args: argparse.Namespace) -> int:
    """Abre um chamado novo, com severidade opcional via catalogo.

    Open a new ticket, with optional default severity from the catalog.
    """
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        severidade = args.severidade
        if severidade and severidade not in modelo.SEVERIDADES:
            raise ErroUso(
                "severidade invalida / invalid severity "
                f"(esperado: {', '.join(modelo.SEVERIDADES)})"
            )
        categoria = args.categoria
        catalogos = _carregar_catalogo(args.dados)
        nomes_categoria = {str(c.get("nome")) for c in (catalogos or {}).get("categorias", [])}
        if categoria and catalogos and categoria not in nomes_categoria:
            raise ErroUso(
                f"categoria nao encontrada no catalogo / category not in catalog: {categoria}"
            )
        if not severidade:
            if categoria and catalogos:
                for c in catalogos.get("categorias", []):
                    if c.get("nome") == categoria:
                        severidade = str(c.get("severidade_padrao", "media"))
                        break
            if not severidade:
                severidade = "media"
        if args.ativo and inventario.buscar(conex, args.ativo) is None:
            raise ErroUso(f"ativo nao encontrado / asset not found: {args.ativo}")
        if not args.titulo or not args.titulo.strip():
            raise ErroUso("titulo obrigatoria / title is required")
        solicitante_id = banco.garantir_usuario(conex, args.solicitante)
        criado = _parse_data(args.marca) if args.marca else _agora_utc()
        novo = banco.abrir_chamado(
            conex,
            titulo=args.titulo.strip(),
            descricao=(args.descricao or "").strip(),
            severidade=severidade,
            categoria=categoria,
            solicitante_id=solicitante_id,
            ativo_codigo=args.ativo,
            criado_em=criado,
        )
        print(f"Chamado #{novo} criado / ticket #{novo} created")
        print(f"  severidade: {severidade} | categoria: {categoria or '-'} | ativo: {args.ativo or '-'}")
        return 0
    finally:
        conex.close()


def _mostra_tabela(tickets: list[modelo.Ticket]) -> None:
    # Larguras fixas: saida deterministica, sem tabulacao de terminal.
    cab = "ID   SEVERIDADE STATUS         ATIVO          CRIADO                 TITULO"
    sep = "---- ---------- -------------- -------------  ---------------------  ------------------------------"
    print(cab)
    print(sep)
    for t in tickets:
        titulo = t.titulo if len(t.titulo) <= 36 else t.titulo[:33] + "..."
        ativo = t.ativo.codigo if t.ativo else "-"
        print(
            f"{t.id:<4} {t.severidade:<10} {t.status:<14} {ativo:<15} "
            f"{t.criado_em.strftime('%Y-%m-%dT%H:%M:%SZ'):<21} {titulo:<36}"
        )


def cmd_listar(args: argparse.Namespace) -> int:
    """Lista chamados; abertos seguem a ordem da fila.

    List tickets; open ones follow the queue order.
    """
    if args.status and args.status not in modelo.STATUS:
        raise ErroUso(f"status invalido / invalid status: {args.status}")
    if args.severidade and args.severidade not in modelo.SEVERIDADES:
        raise ErroUso(
            f"severidade invalida / invalid severity (esperado: {', '.join(modelo.SEVERIDADES)})"
        )
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        todos = banco.carregar_tickets(conex)

        def passa(t: modelo.Ticket) -> bool:
            if args.status and t.status != args.status:
                return False
            if args.severidade and t.severidade != args.severidade:
                return False
            if args.ativo and (t.ativo is None or t.ativo.codigo != args.ativo):
                return False
            return True

        abertos = fila.ordenar_fila([t for t in todos if t.eh_aberto() and passa(t)])
        fechados = sorted(
            (t for t in todos if not t.eh_aberto() and passa(t)),
            key=lambda t: (t.resolvido_em or t.criado_em, t.id),
        )
        mistura = abertos + fechados
        shown = mistura[: args.limit]
        if not shown:
            print("Nenhum chamado / no tickets")
        else:
            _mostra_tabela(shown)
        print(f"\nTOTAL: {len(mistura)} chamado(s) / ticket(s)")
        return 0
    finally:
        conex.close()


def cmd_responder(args: argparse.Namespace) -> int:
    """Registra a primeira resposta de um chamado.

    Record the first answer of a ticket.
    """
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        if args.agente:
            agente = args.agente
        else:
            # Sem agente dado: balanceia por carga atual, empate alfabetico.
            equipes = _equipes_do_catalogo(args.dados)
            cargas = banco.cargas_por_agente(conex)
            agente = fila.atribuir_proximo(equipes, cargas)
        quando = _parse_data(args.marca) if args.marca else _agora_utc()
        banco.responder_chamado(conex, args.id, agente, quando)
        print(
            f"Chamado #{args.id} respondido em {quando.strftime('%Y-%m-%dT%H:%M:%SZ')} por {agente} "
            f"/ ticket #{args.id} answered by {agente}"
        )
        return 0
    finally:
        conex.close()


def cmd_resolver(args: argparse.Namespace) -> int:
    """Resolve um chamado aberto.

    Resolve an open ticket.
    """
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        quando = _parse_data(args.marca) if args.marca else _agora_utc()
        banco.resolver_chamado(conex, args.id, args.agente, quando, args.solucao)
        print(f"Chamado #{args.id} resolvido / ticket #{args.id} resolved")
        return 0
    finally:
        conex.close()


def cmd_inventario(args: argparse.Namespace) -> int:
    """Lista ou cadastra equipamentos do inventario.

    List or register equipment in the inventory.
    """
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        if args.adicionar:
            faltando = [
                nome
                for nome, valor in (
                    ("--tipo", args.tipo),
                    ("--marca", args.marca),
                    ("--modelo", args.modelo),
                    ("--local", args.local),
                )
                if not valor
            ]
            if faltando:
                raise ErroUso(
                    "adicionar exige --tipo --marca --modelo --local / "
                    f"adicionar requires --tipo --marca --modelo --local (faltando / missing: {', '.join(faltando)})"
                )
            inventario.adicionar(
                conex,
                modelo.Equipamento(
                    codigo=args.adicionar,
                    tipo=args.tipo,
                    marca=args.marca,
                    modelo=args.modelo,
                    local=args.local,
                ),
            )
            print(f"Equipamento {args.adicionar} cadastrado / equipment {args.adicionar} registered")
            return 0
        contagens = inventario.contar_chamados(conex)
        equipamentos = inventario.listar(conex)
        cab = "CODIGO         TIPO             MARCA  MODELO  LOCAL                    STATUS   CHAMADOS"
        print("INVENTARIO:")
        print(cab)
        print("-" * len(cab))
        for e in equipamentos:
            print(
                f"{e.codigo:<14} {e.tipo:<15} {e.marca:<6} {e.modelo:<8} "
                f"{e.local:<24} {e.status:<8} {contagens.get(e.codigo, 0):<8}"
            )
        print(f"\nTOTAL: {len(equipamentos)} equipamento(s)")
        return 0
    finally:
        conex.close()


def cmd_relatorio(args: argparse.Namespace) -> int:
    """Gera o relatorio de desempenho (Markdown).

    Generate the performance report (Markdown).
    """
    banco.garantir_banco(args.banco, args.dados)
    conex = banco.abrir(args.banco)
    try:
        referencia = _parse_data(args.referencia) if args.referencia else None
        rel = relatorio.gerar(conex, referencia=referencia, top=args.top)
        tipos = relatorio.tipos_de_ativos(conex)
        texto = relatorio.markdown(rel, tipos)
        print(texto, end="")
        if args.saida:
            destino = Path(args.saida)
            if destino.parent and not destino.parent.exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
            print(f"\nRelatorio salvo em: {args.saida} / report saved to: {args.saida}")
        return 0
    finally:
        conex.close()


def cmd_servidor(args: argparse.Namespace) -> int:
    """Sobe o servidor HTTP local (http.server).

    Start the local HTTP server (http.server).
    """
    server = servidor.criar_servidor(args.banco, args.dados, host=args.host, porta=args.porta)
    porta = servidor.porta_do_server(server)
    print(f"Servidor no ar em http://{args.host}:{porta} / server up at http://{args.host}:{porta}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Servidor encerrado / server stopped")
    return 0


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def _adiciona_opcoes_banco(p: argparse.ArgumentParser) -> None:
    p.add_argument("--banco", default="dados/helpdesk.sqlite",
                   help="caminho do banco SQLite / SQLite database path (default: dados/helpdesk.sqlite)")
    p.add_argument("--dados", default="dados",
                   help="pasta com os seeds YAML / folder with the YAML seeds (default: dados)")


def build_parser() -> argparse.ArgumentParser:
    """Monta o parser da CLI. / Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="helpdesk",
        description=(
            "Sistema local de chamados: abertura, fila, SLA por severidade, inventario "
            "e relatorio de desempenho. "
            "Local ticket system: open tickets, queue, SLA per severity, inventory "
            "and performance report."
        ),
    )
    parser.add_argument("--versao", action="version", version=f"helpdesk {__version__}")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO")

    p_abrir = sub.add_parser(
        "abrir",
        help="abre um chamado / open a ticket",
        description="Abre um chamado aberto, com severidade e opcionalmente categoria, ativo e solicitante. "
                    "Open a ticket with severity and optional category, asset and requester.",
    )
    p_abrir.add_argument("--titulo", required=True, help="titulo do chamado / ticket title")
    p_abrir.add_argument("--descricao", default="", help="descricao do problema / problem description")
    # sem choices: a validacao sai bilingue (ver cmd_abrir)
    p_abrir.add_argument("--severidade",
                         help="severidade: critica, alta, media, baixa; sem o flag, usa o padrao da categoria / severity; defaults to the category one")
    p_abrir.add_argument("--categoria", help="categoria do catalogo / catalog category")
    p_abrir.add_argument("--ativo", help="codigo do ativo do inventario / inventory asset code")
    p_abrir.add_argument("--solicitante", required=True, help="nome do solicitante / requester name")
    p_abrir.add_argument("--marca", help="marca a data de abertura (ISO-8601 Z) / set the opening timestamp (ISO-8601 Z)")
    _adiciona_opcoes_banco(p_abrir)
    p_abrir.set_defaults(func=cmd_abrir)

    p_listar = sub.add_parser(
        "listar",
        help="lista chamados (abertos em ordem de fila) / list tickets (open ones in queue order)",
        description="Lista chamados; abertos saem em ordem de severidade e tempo de espera. "
                    "List tickets; open ones come ordered by severity and waiting time.",
    )
    p_listar.add_argument("--status", help="filtra por status / filter by status")
    p_listar.add_argument("--severidade", help="filtra por severidade / filter by severity")
    p_listar.add_argument("--ativo", help="filtra por codigo de ativo / filter by asset code")
    p_listar.add_argument("--limit", type=int, default=100, help="quantidade maxima de linhas / max rows")
    _adiciona_opcoes_banco(p_listar)
    p_listar.set_defaults(func=cmd_listar)

    p_responder = sub.add_parser(
        "responder",
        help="registra a primeira resposta de um chamado / record the first answer of a ticket",
        description="Registra a primeira resposta e move o chamado para em_atendimento. "
                    "Record the first answer and move the ticket to in-progress.",
    )
    p_responder.add_argument("id", type=int, help="id do chamado / ticket id")
    p_responder.add_argument("--agente", help="agente da resposta; sem o flag, atribui pelo menor cargo "
                                              "/ answering agent; defaults to the least-loaded one")
    p_responder.add_argument("--marca", help="marca a hora da resposta (ISO-8601 Z) / set the answer timestamp")
    _adiciona_opcoes_banco(p_responder)
    p_responder.set_defaults(func=cmd_responder)

    p_resolver = sub.add_parser(
        "resolver",
        help="resolve um chamado aberto / resolve an open ticket",
        description="Resolve um chamado aberto; responde-o junto se ainda nao tinha resposta. "
                    "Resolve an open ticket; answer it at once when it never had a first answer.",
    )
    p_resolver.add_argument("id", type=int, help="id do chamado / ticket id")
    p_resolver.add_argument("--solucao", help="texto da solucao / solution text")
    p_resolver.add_argument("--agente", help="agente que resolve / resolving agent")
    p_resolver.add_argument("--marca", help="marca a hora da resolucao (ISO-8601 Z) / set the resolution timestamp")
    _adiciona_opcoes_banco(p_resolver)
    p_resolver.set_defaults(func=cmd_resolver)

    p_inv = sub.add_parser(
        "inventario",
        help="lista ou cadastra equipamentos / list or register equipment",
        description="Lista o inventario com contagem de chamados por ativo, ou cadastra um ativo novo. "
                    "List the inventory with ticket counts, or register a new asset.",
    )
    p_inv.add_argument("--adicionar", metavar="CODIGO", help="cadastra um ativo novo / register a new asset")
    p_inv.add_argument("--tipo", help="tipo do ativo / asset type")
    p_inv.add_argument("--marca", help="marca do ativo / asset brand")
    p_inv.add_argument("--modelo", help="modelo do ativo / asset model")
    p_inv.add_argument("--local", help="local do ativo / asset location")
    _adiciona_opcoes_banco(p_inv)
    p_inv.set_defaults(func=cmd_inventario)

    p_rel = sub.add_parser(
        "relatorio",
        help="gera o relatorio de desempenho / generate the performance report",
        description=(
            "SLA de resposta e de resolucao, backlog por severidade, MTTR e ativos recorrentes. "
            "Response and resolution SLA, backlog per severity, MTTR and recurring assets."
        ),
    )
    p_rel.add_argument("--saida", help="grava o relatorio em um arquivo .md / write the report to a .md file")
    p_rel.add_argument("--top", type=int, default=relatorio.TOP_PADRAO,
                       help="quantos ativos no top de recorrentes / how many assets in the recurring top")
    p_rel.add_argument("--referencia", help="data de referencia (ISO-8601 Z); padrao: ultimo evento do banco "
                                            "/ reference date (ISO-8601 Z); default: last event in the database")
    _adiciona_opcoes_banco(p_rel)
    p_rel.set_defaults(func=cmd_relatorio)

    p_srv = sub.add_parser(
        "servidor",
        help="sobe o servidor HTTP local / start the local HTTP server",
        description="Servidor HTTP local (http.server) com rotas /, /fila, /chamados, /inventario e /relatorio. "
                    "Local HTTP server (http.server) with routes /, /fila, /chamados, /inventario and /relatorio.",
    )
    p_srv.add_argument("--host", default="127.0.0.1", help="interface de escuta / listening interface")
    p_srv.add_argument("--porta", type=int, default=servidor.PORTA_PADRAO,
                       help="porta (0 escolhe uma livre) / port (0 picks a free one)")
    _adiciona_opcoes_banco(p_srv)
    p_srv.set_defaults(func=cmd_servidor)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Ponto de entrada da CLI. / CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except ErroUso as e:
        print(f"Erro de uso / usage error: {e}", file=sys.stderr)
        return 2
    except (LookupError, ValueError) as e:
        print(f"Erro / error: {e}", file=sys.stderr)
        return 1
    except (OSError, FileNotFoundError) as e:
        print(f"Erro ao acessar arquivos / file access error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
