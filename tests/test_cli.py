"""Testes da CLI: subcomandos, codigos de saida e erros bilingues.

Tests for the CLI: subcommands, exit codes and bilingual errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helpdesk.cli import main

DADOS = Path(__file__).resolve().parents[1] / "dados"


def ops(tmp_path: Path) -> list[str]:
    # todo teste aponta para banco temporario e seeds reais
    return ["--banco", str(tmp_path / "hd.sqlite"), "--dados", str(DADOS)]


def seed() -> dict:
    return yaml.safe_load((DADOS / "chamados-semente.yaml").read_text(encoding="utf-8"))


def test_help_raiz() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


@pytest.mark.parametrize(
    "cmd", ["abrir", "listar", "responder", "resolver", "inventario", "relatorio", "servidor"]
)
def test_help_de_cada_subcomando(cmd: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main([cmd, "--help"])
    assert exc.value.code == 0


def test_sem_subcomando_retorna_dois(capsys) -> None:
    assert main([]) == 2
    assert "helpdesk" in capsys.readouterr().out.lower()


def test_roundtrip_abrir_responder_resolver(tmp_path: Path, capsys) -> None:
    args = ops(tmp_path)
    assert (
        main(
            [
                "abrir",
                "--titulo", "Teste de roundtrip",
                "--descricao", "chamado criado pelo teste",
                "--severidade", "critica",
                "--solicitante", "Zeca Silva",
                "--marca", "2026-01-05T08:00:00Z",
                *args,
            ]
        )
        == 0
    )
    assert "Chamado #133 criado" in capsys.readouterr().out

    assert main(["responder", "133", "--agente", "Time A", "--marca", "2026-01-05T08:30:00Z", *args]) == 0
    out = capsys.readouterr().out
    assert "ticket #133 answered" in out

    assert main(["resolver", "133", "--solucao", "Corrigido no teste", "--marca", "2026-01-05T10:00:00Z", *args]) == 0
    assert "ticket #133 resolved" in capsys.readouterr().out

    assert main(["listar", "--status", "resolvido", "--limit", "500", *args]) == 0
    assert "133" in capsys.readouterr().out


def test_abrir_severidade_invalida_retorna_dois(tmp_path: Path, capsys) -> None:
    codigo = main(
        [
            "abrir",
            "--titulo", "x",
            "--solicitante", "Zeca Silva",
            "--severidade", "urgente",
            *ops(tmp_path),
        ]
    )
    assert codigo == 2
    assert "invalid severity" in capsys.readouterr().err


def test_abrir_ativo_inexistente_retorna_dois(tmp_path: Path, capsys) -> None:
    codigo = main(
        [
            "abrir",
            "--titulo", "x",
            "--solicitante", "Zeca Silva",
            "--ativo", "NAO-EXISTE",
            *ops(tmp_path),
        ]
    )
    assert codigo == 2
    assert "asset not found" in capsys.readouterr().err


def test_abrir_categoria_usa_severidade_do_catalogo(tmp_path: Path, capsys) -> None:
    codigo = main(
        [
            "abrir",
            "--titulo", "Servico fora do ar",
            "--solicitante", "Zeca Silva",
            "--categoria", "Servico Caido",
            *ops(tmp_path),
        ]
    )
    assert codigo == 0
    assert "severidade: critica" in capsys.readouterr().out


def test_responder_chamado_inexistente_retorna_um(tmp_path: Path, capsys) -> None:
    codigo = main(["responder", "9999", *ops(tmp_path)])
    assert codigo == 1
    assert "ticket not found" in capsys.readouterr().err


def test_responder_chamado_ja_respondido_retorna_um(tmp_path: Path, capsys) -> None:
    ja_respondido = next(c["id"] for c in seed()["chamados"] if c.get("primeira_resposta_em"))
    codigo = main(["responder", str(ja_respondido), *ops(tmp_path)])
    assert codigo == 1
    assert "already answered" in capsys.readouterr().err


def test_resolver_chamado_ja_resolvido_retorna_um(tmp_path: Path, capsys) -> None:
    ja_resolvido = next(c["id"] for c in seed()["chamados"] if c["status"] == "resolvido")
    codigo = main(["resolver", str(ja_resolvido), *ops(tmp_path)])
    assert codigo == 1
    assert "already resolved" in capsys.readouterr().err


def test_listar_invalido_retorna_dois(tmp_path: Path, capsys) -> None:
    assert main(["listar", "--status", "arquivado", *ops(tmp_path)]) == 2
    assert "invalid status" in capsys.readouterr().err


def test_inventario_lista(tmp_path: Path, capsys) -> None:
    assert main(["inventario", *ops(tmp_path)]) == 0
    saida = capsys.readouterr().out
    assert "SRV-MAIL-01" in saida
    assert "TOTAL: 12" in saida


def test_inventario_adicionar(tmp_path: Path, capsys) -> None:
    args = ops(tmp_path)
    assert main(
        [
            "inventario",
            "--adicionar", "NB-77",
            "--tipo", "Laptop",
            "--marca", "Prisma",
            "--modelo", "T14",
            "--local", "TI",
            *args,
        ]
    ) == 0
    assert "equipment NB-77 registered" in capsys.readouterr().out
    assert main(["inventario", *args]) == 0
    assert "NB-77" in capsys.readouterr().out


def test_inventario_adicionar_sem_atributos_retorna_dois(tmp_path: Path, capsys) -> None:
    codigo = main(["inventario", "--adicionar", "NB-78", *ops(tmp_path)])
    assert codigo == 2
    assert "adicionar requires" in capsys.readouterr().err


def test_relatorio_grava_arquivo(tmp_path: Path, capsys) -> None:
    saida = tmp_path / "relatorio.md"
    assert main(["relatorio", "--saida", str(saida), *ops(tmp_path)]) == 0
    texto = saida.read_text(encoding="utf-8")
    assert "Relatorio de desempenho" in texto
    assert "report saved to" in capsys.readouterr().out


def test_relatorio_referencia_invalida_retorna_dois(tmp_path: Path, capsys) -> None:
    assert main(["relatorio", "--referencia", "amanha", *ops(tmp_path)]) == 2
    assert "invalid timestamp" in capsys.readouterr().err


def test_relatorio_referencia_explicita_muda_a_saida(tmp_path: Path, capsys) -> None:
    args = ops(tmp_path)
    assert main(["relatorio", "--referencia", "2026-01-05T08:00:00Z", *args]) == 0
    cedo = capsys.readouterr().out
    assert main(["relatorio", "--referencia", "2026-01-25T00:00:00Z", *args]) == 0
    tarde = capsys.readouterr().out
    # em referencias diferentes, a linha de abertos estourados muda
    assert "Abertos ja estourados" in cedo and "Abertos ja estourados" in tarde
    assert cedo != tarde


def test_banco_caminho_inacessivel_retorna_dois(tmp_path: Path, capsys) -> None:
    # pasta de dados sem seeds: seed file missing
    assert main(["listar", "--banco", str(tmp_path / "b.sqlite"), "--dados", str(tmp_path), ]) == 2
    assert "seed file missing" in capsys.readouterr().err or "file access error" in capsys.readouterr().err
