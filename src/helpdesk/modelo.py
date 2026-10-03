"""Modelos de dados do helpdesk: Ticket, Usuario e Equipamento.

Data models for the helpdesk: Ticket, Usuario and Equipamento.

Convencao de horario: todas as datas sao UTC e ficam na memoria como
datetime "naive" (sem tzinfo); as strings persistidas usam sufixo "Z".
Time convention: every datetime is UTC and kept naive in memory; persisted
strings carry the "Z" suffix.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

SEVERIDADES = ("critica", "alta", "media", "baixa")

STATUS_ABIERTO = "aberto"
STATUS_EM_ATENDIMENTO = "em_atendimento"
STATUS_RESOLVIDO = "resolvido"
STATUS_FECHADO = "fechado"
STATUS = (STATUS_ABIERTO, STATUS_EM_ATENDIMENTO, STATUS_RESOLVIDO, STATUS_FECHADO)
# Chamados que ainda ocupam a fila (backlog).
ABERTOS = (STATUS_ABIERTO, STATUS_EM_ATENDIMENTO)


def para_dt(valor: str) -> datetime:
    """Converte string ISO-8601 (UTC, sufixo Z) em datetime naive.

    Parse an ISO-8601 UTC string into a naive datetime.
    """
    dt = datetime.fromisoformat(valor)
    return dt.replace(tzinfo=None)


def para_iso(dt: datetime) -> str:
    """Converte datetime UTC em ISO-8601 com sufixo Z.

    Format an UTC datetime as ISO-8601 with a Z suffix.
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Usuario:
    """Pessoa que abre chamados. / Person who opens tickets."""

    id: int
    nome: str
    email: str
    departamento: str

    @classmethod
    def criar(cls, nome: str, id_: int, departamento: str = "Nao informado") -> "Usuario":
        """Cria um usuario com e-mail derivado do nome (deterministico).

        Build a user with an e-mail derived from the name (deterministic).
        """
        base = nome.strip().lower().replace(" ", ".").replace("-", "")
        email = f"{base}@empresaexemplo.com.br"
        return cls(id=id_, nome=nome.strip(), email=email, departamento=departamento)


@dataclass
class Equipamento:
    """Item do inventario, referenciado pelos chamados via codigo.

    Inventory item, referenced by tickets through its code.
    """

    codigo: str
    tipo: str
    marca: str
    modelo: str
    local: str
    status: str = "ativo"


@dataclass
class Ticket:
    """Chamado do helpdesk, com ciclo aberto -> em_atendimento -> resolvido.

    Helpdesk ticket, with the cycle open -> in_progress -> resolved.
    """

    id: int
    titulo: str
    descricao: str
    severidade: str
    status: str
    criado_em: datetime
    primeira_resposta_em: Optional[datetime] = None
    resolvido_em: Optional[datetime] = None
    solicitante: Optional[Usuario] = None
    ativo: Optional[Equipamento] = None
    agente: Optional[str] = None
    categoria: Optional[str] = None
    solucao: Optional[str] = None

    def __post_init__(self) -> None:
        # Validacao leve nos modelos: erro cedo, erro claro.
        if self.severidade not in SEVERIDADES:
            raise ValueError(
                f"severidade invalida: {self.severidade} / invalid severity: {self.severidade}"
            )
        if self.status not in STATUS:
            raise ValueError(f"status invalido: {self.status} / invalid status: {self.status}")
        if self.primeira_resposta_em is not None and self.primeira_resposta_em < self.criado_em:
            raise ValueError("primeira resposta antes da abertura / first response before creation")
        if self.resolvido_em is not None and self.resolvido_em < self.criado_em:
            raise ValueError("resolucao antes da abertura / resolution before creation")

    def eh_aberto(self) -> bool:
        """True enquanto o chamado ocupa a fila.

        True while the ticket still occupies the queue.
        """
        return self.status in ABERTOS

    def tempo_espera(self, agora: datetime) -> timedelta:
        """Tempo decorrido desde a abertura ate ``agora``.

        Time elapsed since creation up to ``agora``.
        """
        return agora - self.criado_em

    def duracao_resolucao(self) -> Optional[timedelta]:
        """Tempo da abertura a resolucao; None se ainda nao resolvido.

        Time from creation to resolution; None when not resolved yet.
        """
        if self.resolvido_em is None:
            return None
        return self.resolvido_em - self.criado_em
