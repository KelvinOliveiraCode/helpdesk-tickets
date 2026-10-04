"""Confere encoding dos arquivos de texto versionados.

Check the encoding of every text file in the repository.

Um BOM UTF-8 no inicio, um caractere de substituicao (U+FFFD) ou um
bloco CJK dentro de um arquivo de codigo indica corrompimento. Falhar
aqui evita lixo nos diffs do GitHub.

Um U+FFFD e um caractere de substituicao. Um bloco CJK e texto em
japones, coreano ou chines. Nenhum pertence a este repositorio.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Raiz do repositorio.
RAIZ = Path(__file__).resolve().parent.parent

#: Extensoes varridas. Binarios ficam de fora de proposito.
EXTENSOES = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml",
    ".toml", ".cfg", ".ini", ".ps1",
}

#: Extensões binárias ignoradas explicitamente.
BINARIAS = {".png", ".jpg", ".mp4", ".woff", ".woff2"}

#: Diretorios e arquivos ignorados.
IGNORADOS = {
    ".git", ".pytest_cache", "__pycache__", "htmlcov", ".venv",
    "venv", "build", "dist", ".coverage", "coverage.xml",
}

#: Intervalo de ideogramas CJK.
CJK = range(0x3000, 0x9FFF + 1)

#: BOM UTF-8 (U+FEFF).
BOM = 0xFEFF

#: Caractere de substituicao.
SUBSTITUICAO = 0xFFFD


def varrer(raiz: Path = RAIZ) -> tuple[list[tuple[str, int, str]], int]:
    """Procura arquivos de texto com caractere invalido.

    Find text files holding an invalid character.

    Args:
        raiz: Diretorio a varrer.

    Returns:
        Tupla de ``(problemas, total)`` onde ``problemas`` e uma lista
        de ``(caminho, linha, motivo)`` e ``total`` e a quantidade de
        arquivos conferidos.
    """
    problemas: list[tuple[str, int, str]] = []
    total = 0
    for caminho in sorted(raiz.rglob("*")):
        if not caminho.is_file():
            continue
        if any(parte in IGNORADOS for parte in caminho.parts):
            continue
        if caminho.suffix.lower() in BINARIAS:
            continue
        if (caminho.suffix.lower() not in EXTENSOES
                and caminho.name != ".gitignore"):
            continue
        total += 1
        try:
            texto = caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            problemas.append((
                str(caminho.relative_to(raiz)), 0,
                f"nao decodifica como UTF-8: {exc}",
            ))
            continue
        if texto.startswith("\ufeff"):
            problemas.append((
                str(caminho.relative_to(raiz)), 0,
                "BOM UTF-8 no inicio do arquivo",
            ))
        for numero, linha in enumerate(texto.splitlines(), 1):
            for caractere in linha:
                ponto = ord(caractere)
                if ponto == SUBSTITUICAO:
                    problemas.append((
                        str(caminho.relative_to(raiz)), numero,
                        "caractere de substituicao U+FFFD",
                    ))
                    break
                if ponto in CJK:
                    problemas.append((
                        str(caminho.relative_to(raiz)), numero,
                        f"ideograma CJK U+{ponto:04X}",
                    ))
                    break
    return problemas, total


def main() -> int:
    """Executa a varredura e reporta.

    Run the sweep and report.
    """
    problemas, total = varrer()
    if not problemas:
        print(
            f"encoding ok: {total} arquivo(s) conferidos,"
            " nenhum U+FFFD, nenhum BOM e nenhum ideograma CJK"
        )
        return 0
    print(
        f"encoding FALHOU: {len(problemas)} problema(s) em"
        f" {total} arquivo(s) conferidos"
    )
    for caminho, linha, motivo in problemas:
        onde = f"{caminho}:{linha}" if linha else caminho
        print(f"  {onde}: {motivo}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
