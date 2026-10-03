"""Persistencia local em SQLite e populacao a partir dos seeds de ``dados/``.

Local SQLite persistence and population from the YAML seeds in ``dados/``.

Regras de convivencia com a CLI:
- o arquivo de banco e criado so quando nao existe;
- um banco criado mas vazio recebe o seed exatamente uma vez;
- todo acesso abre e fecha conexao (nada fica aberto entre comandos).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .modelo import Equipamento, Ticket, Usuario, para_dt, para_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    departamento TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equipamentos (
    codigo TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    local TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativo'
);

CREATE TABLE IF NOT EXISTS chamados (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    severidade TEXT NOT NULL CHECK (severidade IN ('critica', 'alta', 'media', 'baixa')),
    status TEXT NOT NULL DEFAULT 'aberto'
        CHECK (status IN ('aberto', 'em_atendimento', 'resolvido', 'fechado')),
    categoria TEXT,
    solicitante_id INTEGER NOT NULL REFERENCES usuarios (id),
    ativo_codigo TEXT REFERENCES equipamentos (codigo),
    agente TEXT,
    criado_em TEXT NOT NULL,
    primeira_resposta_em TEXT,
    resolvido_em TEXT,
    solucao TEXT
);

CREATE INDEX IF NOT EXISTS idx_chamados_fila ON chamados (severidade, criado_em);
CREATE INDEX IF NOT EXISTS idx_chamados_ativo ON chamados (ativo_codigo);
"""


def _le_yaml(caminho: Path) -> dict:
    # Erro de arquivo vira mensagem clara bilingue.
    try:
        bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(
            f"arquivo de dados ausente / seed file missing: {caminho.name}"
        ) from None
    if not isinstance(bruto, dict):
        raise ValueError(f"seed invalido (esperado mapeamento) / invalid seed (mapping expected): {caminho.name}")
    return bruto


def abrir(caminho: str | Path) -> sqlite3.Connection:
    """Abre conexao SQLite com row_factory de nome.

    Open a SQLite connection with a name-based row factory.
    """
    conex = sqlite3.connect(str(caminho))
    conex.row_factory = sqlite3.Row
    return conex


def criar(caminho: str | Path) -> None:
    """Cria o esquema do banco (idempotente).

    Create the schema (idempotent).
    """
    conex = sqlite3.connect(str(caminho))
    try:
        conex.executescript(SCHEMA)
        conex.commit()
    finally:
        conex.close()


def esta_vazio(conex: sqlite3.Connection) -> bool:
    """True se ainda nao ha equipamentos no banco.

    True when no equipment row exists yet.
    """
    linha = conex.execute("SELECT COUNT(*) AS n FROM equipamentos").fetchone()
    return int(linha["n"]) == 0


def garantir_banco(caminho: str | Path, pasta_dados: str | Path) -> None:
    """Garante banco criado e semeado; nao reescreve banco ja populado.

    Ensure the database exists and is seeded; never rewrite a populated one.
    """
    caminho = Path(caminho)
    if caminho.parent and not caminho.parent.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)
    if not caminho.exists():
        criar(caminho)
    conex = abrir(caminho)
    try:
        if esta_vazio(conex):
            popular_do_seed(conex, pasta_dados)
    finally:
        conex.close()


def popular_do_seed(conex: sqlite3.Connection, pasta_dados: str | Path) -> int:
    """Popula usuarios, equipamentos e chamados a partir dos seeds YAML.

    Populate users, equipment and tickets from the YAML seeds.

    Levanta ``ValueError`` se o banco ja tiver dados (evita seed duplo).
    Raises ``ValueError`` when the database is not empty.
    """
    if not esta_vazio(conex):
        raise ValueError(
            "banco ja possui dados; populacao recusada / database already seeded, refusing to populate"
        )
    pasta = Path(pasta_dados)
    seed_chamados = _le_yaml(pasta / "chamados-semente.yaml")
    seed_inventario = _le_yaml(pasta / "inventario-semente.yaml")

    usuarios = seed_chamados.get("usuarios") or []
    for u in usuarios:
        conex.execute(
            "INSERT INTO usuarios (id, nome, email, departamento) VALUES (?, ?, ?, ?)",
            (int(u["id"]), u["nome"], u["email"], u.get("departamento", "Nao informado")),
        )

    equipamentos = seed_inventario.get("equipamentos") or []
    codigos_ativos: set[str] = set()
    for e in equipamentos:
        codigos_ativos.add(e["codigo"])
        conex.execute(
            "INSERT INTO equipamentos (codigo, tipo, marca, modelo, local, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                e["codigo"],
                e["tipo"],
                e.get("marca", ""),
                e.get("modelo", ""),
                e.get("local", ""),
                e.get("status", "ativo"),
            ),
        )

    ids_usuarios = {int(u["id"]) for u in usuarios}
    total = 0
    for c in seed_chamados.get("chamados") or []:
        ativo = c.get("ativo")
        if ativo is not None and ativo not in codigos_ativos:
            raise ValueError(
                f"chamado #{c.get('id')} referencia ativo fora do inventario / "
                f"ticket #{c.get('id')} references an asset missing from the inventory"
            )
        solicitante = int(c.get("solicitante", 0))
        if solicitante not in ids_usuarios:
            raise ValueError(
                f"chamado #{c.get('id')} referencia usuario ausente do seed / "
                f"ticket #{c.get('id')} references a user missing from the seed"
            )
        conex.execute(
            "INSERT INTO chamados "
            "(id, titulo, descricao, severidade, status, categoria, solicitante_id, "
            " ativo_codigo, agente, criado_em, primeira_resposta_em, resolvido_em, solucao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                int(c["id"]),
                c["titulo"],
                c["descricao"],
                c["severidade"],
                c["status"],
                c.get("categoria"),
                solicitante,
                ativo,
                c.get("agente"),
                c["criado_em"],
                c.get("primeira_resposta_em"),
                c.get("resolvido_em"),
                c.get("solucao"),
            ),
        )
        total += 1
    conex.commit()
    return total


def _de_linha(l: sqlite3.Row) -> Ticket:
    solicitante: Optional[Usuario] = None
    if l["u_nome"] is not None:
        solicitante = Usuario(
            id=int(l["solicitante_id"]),
            nome=l["u_nome"],
            email=l["u_email"],
            departamento=l["u_dep"],
        )
    ativo: Optional[Equipamento] = None
    if l["e_codigo"] is not None:
        ativo = Equipamento(
            codigo=l["e_codigo"],
            tipo=l["e_tipo"],
            marca=l["e_marca"],
            modelo=l["e_modelo"],
            local=l["e_local"],
            status=l["e_status"],
        )
    return Ticket(
        id=int(l["id"]),
        titulo=l["titulo"],
        descricao=l["descricao"],
        severidade=l["severidade"],
        status=l["status"],
        criado_em=para_dt(l["criado_em"]),
        primeira_resposta_em=(
            para_dt(l["primeira_resposta_em"]) if l["primeira_resposta_em"] else None
        ),
        resolvido_em=para_dt(l["resolvido_em"]) if l["resolvido_em"] else None,
        solicitante=solicitante,
        ativo=ativo,
        agente=l["agente"],
        categoria=l["categoria"],
        solucao=l["solucao"],
    )


def carregar_tickets(conex: sqlite3.Connection) -> list[Ticket]:
    """Carrega todos os chamados, com solicitante e ativo incorporados.

    Load every ticket with its user and asset embedded.
    """
    linhas = conex.execute(
        """
        SELECT c.*,
               u.nome AS u_nome, u.email AS u_email, u.departamento AS u_dep,
               e.codigo AS e_codigo, e.tipo AS e_tipo, e.marca AS e_marca,
               e.modelo AS e_modelo, e.local AS e_local, e.status AS e_status
        FROM chamados c
        LEFT JOIN usuarios u ON u.id = c.solicitante_id
        LEFT JOIN equipamentos e ON e.codigo = c.ativo_codigo
        ORDER BY c.id
        """
    ).fetchall()
    return [_de_linha(l) for l in linhas]


def buscar_ticket(conex: sqlite3.Connection, ticket_id: int) -> Optional[Ticket]:
    """Busca um chamado por id; None se nao existe.

    Look up one ticket by id; None when absent.
    """
    for t in carregar_tickets(conex):
        if t.id == ticket_id:
            return t
    return None


def proximo_id(conex: sqlite3.Connection) -> int:
    """Proximo id numerico de chamado.

    Next numeric ticket id.
    """
    linha = conex.execute("SELECT COALESCE(MAX(id) + 1, 1) AS n FROM chamados").fetchone()
    return int(linha["n"])


def garantir_usuario(conex: sqlite3.Connection, nome: str, departamento: str = "Nao informado") -> int:
    """Retorna o id do usuario; cria o usuario quando ele nao existe.

    Return the user's id; create the user when it does not exist yet.
    """
    linha = conex.execute(
        "SELECT id FROM usuarios WHERE nome = ?", (nome.strip(),)
    ).fetchone()
    if linha is not None:
        return int(linha["id"])
    # id sequencial deterministico: o maximo atual + 1
    maximo = conex.execute("SELECT COALESCE(MAX(id) + 1, 1) AS n FROM usuarios").fetchone()
    novo = Usuario.criar(nome, int(maximo["n"]), departamento)
    conex.execute(
        "INSERT INTO usuarios (id, nome, email, departamento) VALUES (?, ?, ?, ?)",
        (novo.id, novo.nome, novo.email, novo.departamento),
    )
    conex.commit()
    return novo.id


def abrir_chamado(
    conex: sqlite3.Connection,
    *,
    titulo: str,
    descricao: str,
    severidade: str,
    categoria: Optional[str],
    solicitante_id: int,
    ativo_codigo: Optional[str],
    criado_em: datetime,
    agente: Optional[str] = None,
) -> int:
    """Cria um chamado aberto e devolve o id.

    Create an open ticket and return its id.
    """
    ticket_id = proximo_id(conex)
    conex.execute(
        "INSERT INTO chamados "
        "(id, titulo, descricao, severidade, status, categoria, solicitante_id, "
        " ativo_codigo, agente, criado_em) "
        "VALUES (?, ?, ?, ?, 'aberto', ?, ?, ?, ?, ?)",
        (
            ticket_id,
            titulo,
            descricao,
            severidade,
            categoria,
            solicitante_id,
            ativo_codigo,
            agente,
            para_iso(criado_em),
        ),
    )
    conex.commit()
    return ticket_id


def responder_chamado(
    conex: sqlite3.Connection,
    ticket_id: int,
    agente: str,
    quando: datetime,
) -> None:
    """Registra a primeira resposta e move o chamado para em_atendimento.

    Record the first answer and move the ticket to in-progress.
    """
    linha = conex.execute(
        "SELECT status, primeira_resposta_em FROM chamados WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    if linha is None:
        raise LookupError(f"chamado nao encontrado / ticket not found: {ticket_id}")
    if linha["primeira_resposta_em"] is not None:
        raise ValueError(
            f"chamado {ticket_id} ja foi respondido / ticket {ticket_id} already answered"
        )
    conex.execute(
        "UPDATE chamados SET status = 'em_atendimento', primeira_resposta_em = ?, agente = ? WHERE id = ?",
        (para_iso(quando), agente, ticket_id),
    )
    conex.commit()


def resolver_chamado(
    conex: sqlite3.Connection,
    ticket_id: int,
    agente: Optional[str],
    quando: datetime,
    solucao: Optional[str] = None,
) -> None:
    """Resolva o chamado; responde-o junto se ainda nao tinha resposta.

    Resolve the ticket; record the first answer as well when it never had one.
    """
    linha = conex.execute(
        "SELECT status, primeira_resposta_em FROM chamados WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    if linha is None:
        raise LookupError(f"chamado nao encontrado / ticket not found: {ticket_id}")
    if linha["status"] in ("resolvido", "fechado"):
        raise ValueError(f"chamado {ticket_id} ja resolvido / ticket {ticket_id} already resolved")
    if linha["primeira_resposta_em"] is None:
        # Resolvo sem responder: a resolucao vale como a primeira resposta.
        conex.execute(
            "UPDATE chamados SET status = 'resolvido', primeira_resposta_em = ?, "
            "resolvido_em = ?, agente = ?, solucao = ? WHERE id = ?",
            (para_iso(quando), para_iso(quando), agente, solucao, ticket_id),
        )
    else:
        conex.execute(
            "UPDATE chamados SET status = 'resolvido', resolvido_em = ?, agente = ?, "
            "solucao = ? WHERE id = ?",
            (para_iso(quando), agente, solucao, ticket_id),
        )
    conex.commit()


def cargas_por_agente(conex: sqlite3.Connection) -> dict[str, int]:
    """Chamados abertos por agente (para balancear atribuicao).

    Open tickets per agent (used to balance assignment).
    """
    linhas = conex.execute(
        "SELECT agente, COUNT(*) AS n FROM chamados "
        "WHERE status IN ('aberto', 'em_atendimento') AND agente IS NOT NULL "
        "GROUP BY agente"
    ).fetchall()
    return {l["agente"]: int(l["n"]) for l in linhas}


def ultima_data_evento(conex: sqlite3.Connection) -> Optional[datetime]:
    """Maior timestamp presente no banco; None se vazio.

    Latest timestamp present in the database; None when empty.
    """
    linha = conex.execute(
        "SELECT MAX(criado_em) AS a FROM chamados"
    ).fetchone()
    if linha["a"] is None:
        return None
    candidates: list[str] = [linha["a"]]
    for campo in ("primeira_resposta_em", "resolvido_em"):
        l2 = conex.execute(f"SELECT MAX({campo}) AS a FROM chamados WHERE {campo} IS NOT NULL").fetchone()
        if l2["a"] is not None:
            candidates.append(l2["a"])
    return para_dt(max(candidates))
