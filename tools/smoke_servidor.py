"""Smoke test manual do servidor HTTP (nao faz parte da suite do pytest).

Manual smoke test for the HTTP server (not part of the pytest suite).

Uso / usage:
    $env:PYTHONPATH = "src"; python tools\\smoke_servidor.py

Sobe o servidor numa porta livre, faz requisicoes reais a 127.0.0.1 e
encerra tudo no finally.
"""

from __future__ import annotations

import json
import tempfile
import threading
import urllib.request
from pathlib import Path

from helpdesk import banco, servidor

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="helpdesk-smoke-"))
    banco_path = tmp / "smoke.sqlite"
    serv = servidor.criar_servidor(banco_path, RAIZ / "dados", host="127.0.0.1", porta=0)
    thread = threading.Thread(target=serv.serve_forever, daemon=True)
    thread.start()
    try:
        porta = servidor.porta_do_server(serv)
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/", timeout=10) as r:
            print("GET /:", json.loads(r.read())["abertos"], "abertos")
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/fila", timeout=10) as r:
            fila = json.loads(r.read())["fila"]
        print("fila top 3:", [(t["severidade"], t["id"]) for t in fila[:3]])
    finally:
        serv.shutdown()
        serv.server_close()
        thread.join(timeout=5)
    print("servidor encerrado limpo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
