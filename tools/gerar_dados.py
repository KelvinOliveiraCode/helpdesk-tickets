"""Gerador deterministico dos seeds de dados do helpdesk.

Deterministic generator for the helpdesk seed data (stdlib only).

Uso / usage:
    python tools/gerar_dados.py

Gera em ``dados/`` / generates in ``dados/``:
    - chamados-semente.yaml       (usuarios + 132 chamados)
    - inventario-semente.yaml     (12 equipamentos)
    - catalogo-servicos.yaml      (categorias, severidade padrao, equipes)

Nada aqui e escrito a mao: os tres arquivos sao materializados por este
script com seed fixo (SEED abaixo), entao o rodar duas vezes produz bytes
identicos. O inventario fica em arquivo separado do arquivo de chamados
porque equipamento e entidade duradoura: ele nao nasce e morre com o
ciclo dos chamados (justificacao em docs/matriz-de-prioridade.md).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260105
BASE = datetime(2026, 1, 5, 8, 0, 0)  # UTC, inicio da janela de eventos

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

# ---------------------------------------------------------------------------
# usuarios ficticios (10)
# ---------------------------------------------------------------------------
USUARIOS = [
    (1, "Ana Duarte", "Financeiro"),
    (2, "Bruno Camara", "Operacoes"),
    (3, "Carla Figueiredo", "Comercial"),
    (4, "Diego Fontes", "RH"),
    (5, "Elisa Ramos", "Diretoria"),
    (6, "Felipe Nogueira", "TI"),
    (7, "Gisele Prado", "Operacoes"),
    (8, "Hugo Sales", "Comercial"),
    (9, "Iara Teixeira", "Financeiro"),
    (10, "Joao Pires", "TI"),
]

EQUIPES = ["Time A", "Time B", "Time C"]

# ---------------------------------------------------------------------------
# inventario (12); contagem de chamados por ativo define os recorrentes
# ---------------------------------------------------------------------------
# (codigo, tipo, marca, modelo, local, status, chamados)
INVENTARIO = [
    ("SRV-MAIL-01", "Servidor", "Prisma", "TX-420", "Data Center - Rack A", "ativo", 22),
    ("SW-CORE-01", "Switch", "Nimbus", "N-9300", "Data Center - Closets", "ativo", 18),
    ("SRV-AD-01", "Servidor", "Prisma", "TX-420", "Data Center - Rack A", "ativo", 12),
    ("VR-001", "Servidor Virtual", "Nimbus", "VE-8", "Data Center - Rack B", "ativo", 12),
    ("SRV-FILE-01", "Servidor", "Vertex", "R740X", "Data Center - Rack B", "ativo", 10),
    ("PDC-LOJA-05", "PC", "Vertex", "O-7090", "Loja - Caixa 5", "ativo", 10),
    ("SW-ACESO-02", "Switch", "Nimbus", "N-2930", "Prancha 3", "ativo", 8),
    ("AP-3F-01", "Access Point", "Aurora", "AC-Lite", "Prancha 3 - Sala 302", "ativo", 8),
    ("IMP-F04-01", "Impressora", "Delta", "M404", "Financeiro - 4 and", "ativo", 8),
    ("MON-OP-02", "Monitor", "Delta", "P24H", "Operacoes - Mesa 2", "inativo", 8),
    ("NB-A32", "Laptop", "Prisma", "T14", "Financeiro - 4 and", "ativo", 8),
    ("TK-012", "Telefone", "Aurora", "T48S", "Comercial - Box 12", "ativo", 8),
]

# ---------------------------------------------------------------------------
# contagem exata por severidade (total 132)
# coluna: total | resolvido | em_atendimento | aberto
# ---------------------------------------------------------------------------
PLANO = {
    "critica": {"total": 15, "resolvido": 12, "em_atendimento": 2, "aberto": 1},
    "alta": {"total": 35, "resolvido": 28, "em_atendimento": 5, "aberto": 2},
    "media": {"total": 45, "resolvido": 37, "em_atendimento": 5, "aberto": 3},
    "baixa": {"total": 37, "resolvido": 27, "em_atendimento": 4, "aberto": 6},
}

# do total de chamados COM resposta (120), quantos estouraram o SLA de resposta
ESTOURO_RESPOSTA_RESOLVIDOS = 26
ESTOURO_RESPOSTA_EM_ATENDIMENTO = 10
# do total de resolvidos (104), quantos estouraram o SLA de resolucao
ESTOURO_RESOLUCAO = 26

PRORRO_RESPOSTA_H = {"critica": 1.0, "alta": 4.0, "media": 8.0, "baixa": 24.0}
PRORRO_RESOLUCAO_H = {"critica": 4.0, "alta": 16.0, "media": 32.0, "baixa": 96.0}

# categoria padrao por ativo
CATEGORIA_ATIVO = {
    "SRV-MAIL-01": "E-mail",
    "SW-CORE-01": "Sem rede",
    "SW-ACESO-02": "Sem rede",
    "AP-3F-01": "Sem rede",
    "SRV-AD-01": "Sistema",
    "SRV-FILE-01": "Sistema",
    "VR-001": "Sistema",
    "IMP-F04-01": "Hardware",
    "MON-OP-02": "Hardware",
    "NB-A32": "Hardware",
    "TK-012": "Hardware",
    "PDC-LOJA-05": "Hardware",
}

TITULOS = {
    "critica": [
        "Servico {ativo} fora do ar",
        "Caida total: {ativo} inacessivel",
        "Produtividade parada por {ativo}",
    ],
    "Sem rede": [
        "Sem rede no terminal proximo de {ativo}",
        "Enlace instavel ligado em {ativo}",
        "Perdi acesso a rede via {ativo}",
    ],
    "E-mail": [
        "Mensagens paradas na fila de {ativo}",
        "Caixa de entrada de {ativo} sem atualizar",
        "Antivirus de {ativo} bloqueando entregas",
    ],
    "Sistema": [
        "Erro na tela inicial de {ativo}",
        "Integracao de {ativo} fora do horario",
        "Backup de {ativo} falhou duas vezes",
    ],
    "Hardware": [
        "{ativo} nao liga no turno da manha",
        "Imagem distorcida em {ativo}",
        "Periferico de {ativo} cortou o turno",
    ],
    "Software": [
        "Planilha travando no turno da manha",
        "Licenca do antivirus expirada no time",
        "App de ponto nao abre na rede local",
    ],
    "Acesso": [
        "Reset de senha para a conta do time",
        "Acesso ao portal interno negado",
    ],
}

DESCRICAO_IMPACTO = [
    "O time inteiro de {depto} ficou parado.",
    "A operacao perdeu meio turno ate a normalizacao.",
    "Dois terminos estao sem acesso desde o inicio do dia.",
    "O setor de {depto} esta trabalhando no papel.",
    "A loja ja atendeu cliente no apontamento manual.",
]


def q(valor: str) -> str:
    """Coloca string em aspas duplas para YAML (escapa aspas e barras).

    Quote a string for YAML (escapes quotes and backslashes).
    """
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def iso(dt: datetime) -> str:
    """Formato ISO-8601 com Z (naive UTC). / ISO-8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def email_de(nome: str) -> str:
    return nome.strip().lower().replace(" ", ".") + "@empresaexemplo.com.br"


def gera(r: random.Random) -> dict:
    """Gera a estrutura completa de chamados.

    Generate the full ticket structure.
    """
    # 1. plano de status por severidade
    por_severidade: dict[str, list[str]] = {}
    for sev, plano in PLANO.items():
        por_severidade[sev] = (
            ["resolvido"] * plano["resolvido"]
            + ["em_atendimento"] * plano["em_atendimento"]
            + ["aberto"] * plano["aberto"]
        )
        assert len(por_severidade[sev]) == plano["total"]

    # 2. pool de ativos conforme contagem do inventario
    pool: list[str] = []
    for codigo, *_resto, contagem in INVENTARIO:
        pool.extend([codigo] * contagem)
    assert len(pool) == sum(p["total"] for p in PLANO.values())
    r.shuffle(pool)

    # 3. esqueleto dos chamados (texto primeiro, timestamps depois)
    esqueleto: list[dict] = []
    for sev, lista in por_severidade.items():
        for status in lista:
            ativo = pool.pop()
            usuario = USUARIOS[r.randrange(len(USUARIOS))]
            user_id, nome, depto = usuario
            categoria = "Servico Caido" if sev == "critica" else (
                "Software" if r.random() < 0.2 else CATEGORIA_ATIVO[ativo]
            )
            chave_titulo = "critica" if sev == "critica" else categoria
            titulo = r.choice(TITULOS[chave_titulo]).format(ativo=ativo)
            descricao = (
                f"Reportado por {nome} ({depto}). "
                f"Problema em {ativo}. "
                f"{r.choice(DESCRICAO_IMPACTO).format(depto=depto)}"
            )
            # chamado aberto ainda nao tem agente atribuido
            esqueleto.append({
                "severidade": sev,
                "status": status,
                "categoria": categoria,
                "solicitante": user_id,
                "ativo": ativo,
                "agente": r.choice(EQUIPES) if status != "aberto" else None,
                "titulo": titulo,
                "descricao": descricao,
            })

    # 4. quem estoura cada relogio de SLA (amostra por indice de chamado)
    n = len(esqueleto)
    respondidos_idx = [i for i in range(n) if esqueleto[i]["status"] != "aberto"]
    estourados_resposta = set(
        r.sample(respondidos_idx, ESTOURO_RESPOSTA_RESOLVIDOS + ESTOURO_RESPOSTA_EM_ATENDIMENTO)
    )
    resolvidos_idx = [i for i in range(n) if esqueleto[i]["status"] == "resolvido"]
    estourados_resolucao = set(r.sample(resolvidos_idx, ESTOURO_RESOLUCAO))

    chamados: list[dict] = []
    for i, base in enumerate(esqueleto):
        sev, status, ativo = base["severidade"], base["status"], base["ativo"]
        entrada = dict(base)
        if status == "resolvido":
            criado = BASE + timedelta(seconds=r.uniform(0, 9 * 86400))
            if i in estourados_resolucao:
                total_h = r.uniform(1.1, 1.9) * PRORRO_RESOLUCAO_H[sev]
            else:
                total_h = r.uniform(0.4, 0.9) * PRORRO_RESOLUCAO_H[sev]
            resolvido = criado + timedelta(hours=total_h)
            if i in estourados_resposta:
                resposta = criado + timedelta(hours=r.uniform(1.15, 1.8) * PRORRO_RESPOSTA_H[sev])
            else:
                resposta = criado + timedelta(hours=r.uniform(0.15, 0.7) * PRORRO_RESPOSTA_H[sev])
            # resposta sempre antes da resolucao
            if resposta >= resolvido:
                resposta = criado + timedelta(minutes=30)
            entrada["criado_em"] = iso(criado)
            entrada["primeira_resposta_em"] = iso(resposta)
            entrada["resolvido_em"] = iso(resolvido)
            entrada["solucao"] = (
                "Suporte acionou o fabricante e trocou a portadora; servico normalizado."
                if sev == "critica"
                else "Situacao normalizada apos reinicio do componente."
            )
        elif status == "em_atendimento":
            criado = BASE + timedelta(seconds=r.uniform(0, 3 * 86400))
            if i in estourados_resposta:
                resposta = criado + timedelta(hours=r.uniform(1.15, 1.8) * PRORRO_RESPOSTA_H[sev])
            else:
                resposta = criado + timedelta(hours=r.uniform(0.15, 0.7) * PRORRO_RESPOSTA_H[sev])
            entrada["criado_em"] = iso(criado)
            entrada["primeira_resposta_em"] = iso(resposta)
        else:  # aberto: sem resposta ainda
            criado = BASE + timedelta(seconds=r.uniform(0, 5 * 86400))
            entrada["criado_em"] = iso(criado)
        chamados.append(entrada)

    # 5. ids sequenciais pela ordem cronologica (com desempate por titulo)
    chamados.sort(key=lambda c: (c["criado_em"], c["titulo"]))
    for i, c in enumerate(chamados, start=1):
        c_ordered = {"id": i}
        c_ordered.update(c)
        chamados[i - 1] = c_ordered
    return {"usuarios": [
        {"id": uid, "nome": nome, "email": email_de(nome), "departamento": depto}
        for uid, nome, depto in USUARIOS
    ], "chamados": chamados}


def escreve_yaml_chamados(dados: dict, caminho: Path) -> None:
    linhas = [
        "# Seed de chamados e usuarios ficticios.",
        f"# Gerado por tools/gerar_dados.py (seed {SEED}); nao editar a mao.",
        "usuarios:",
    ]
    for u in dados["usuarios"]:
        linhas.append(f"  - id: {u['id']}")
        linhas.append(f"    nome: {q(u['nome'])}")
        linhas.append(f"    email: {q(u['email'])}")
        linhas.append(f"    departamento: {q(u['departamento'])}")
    linhas.append("chamados:")
    for c in dados["chamados"]:
        linhas.append(f"  - id: {c['id']}")
        linhas.append(f"    titulo: {q(c['titulo'])}")
        linhas.append(f"    descricao: {q(c['descricao'])}")
        linhas.append(f"    severidade: {q(c['severidade'])}")
        linhas.append(f"    status: {q(c['status'])}")
        linhas.append(f"    categoria: {q(c['categoria'])}")
        linhas.append(f"    solicitante: {c['solicitante']}")
        linhas.append(f"    ativo: {q(c['ativo'])}")
        if c.get("agente"):
            linhas.append(f"    agente: {q(c['agente'])}")
        linhas.append(f"    criado_em: {q(c['criado_em'])}")
        if c.get("primeira_resposta_em"):
            linhas.append(f"    primeira_resposta_em: {q(c['primeira_resposta_em'])}")
        if c.get("resolvido_em"):
            linhas.append(f"    resolvido_em: {q(c['resolvido_em'])}")
        if c.get("solucao"):
            linhas.append(f"    solucao: {q(c['solucao'])}")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def escreve_yaml_inventario(caminho: Path) -> None:
    linhas = [
        "# Seed de inventario ficticio.",
        f"# Gerado por tools/gerar_dados.py (seed {SEED}); nao editar a mao.",
        "equipamentos:",
    ]
    for codigo, tipo, marca, modelo, local, status, _contagem in INVENTARIO:
        linhas.append(f"  - codigo: {q(codigo)}")
        linhas.append(f"    tipo: {q(tipo)}")
        linhas.append(f"    marca: {q(marca)}")
        linhas.append(f"    modelo: {q(modelo)}")
        linhas.append(f"    local: {q(local)}")
        linhas.append(f"    status: {q(status)}")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


CATALOGO = """# Catalogo de servicos do helpdesk: categorias, severidade padrao e equipes.
# Gerado por tools/gerar_dados.py (seed 20260105); nao editar a mao.
categorias:
  - nome: "Sem rede"
    severidade_padrao: "alta"
    descricao: "Falta de conexao, enlace fora ou acesso a rede local"
  - nome: "E-mail"
    severidade_padrao: "media"
    descricao: "Caixa de entrada, envio e filtros de mensagens"
  - nome: "Sistema"
    severidade_padrao: "alta"
    descricao: "ERP, sistemas internos e integracoes"
  - nome: "Hardware"
    severidade_padrao: "baixa"
    descricao: "Notebooks, monitores, impressoras e perifericos"
  - nome: "Software"
    severidade_padrao: "baixa"
    descricao: "Aplicativos de bancada e licencas"
  - nome: "Acesso"
    severidade_padrao: "media"
    descricao: "Senhas, permissoes e contas"
  - nome: "Servico Caido"
    severidade_padrao: "critica"
    descricao: "Servico critico fora do ar"
equipes:
  - "Time A"
  - "Time B"
  - "Time C"
"""


def main() -> int:
    r = random.Random(SEED)
    DADOS.mkdir(parents=True, exist_ok=True)
    dados = gera(r)
    escreve_yaml_chamados(dados, DADOS / "chamados-semente.yaml")
    escreve_yaml_inventario(DADOS / "inventario-semente.yaml")
    (DADOS / "catalogo-servicos.yaml").write_text(CATALOGO, encoding="utf-8")
    total = len(dados["chamados"])
    print(f"Gerados: {total} chamados, {len(USUARIOS)} usuarios, {len(INVENTARIO)} equipamentos")
    print(f"Arquivos: {DADOS / 'chamados-semente.yaml'}")
    print(f"Arquivos: {DADOS / 'inventario-semente.yaml'}")
    print(f"Arquivos: {DADOS / 'catalogo-servicos.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
