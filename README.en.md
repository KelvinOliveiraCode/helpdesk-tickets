<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">

# helpdesk-tickets

Local CLI and HTTP server over SQLite that opens tickets, orders the queue by severity and wait time, measures response and resolution SLA on separate clocks, maintains the equipment inventory and emits the performance report.

## Problem / Why it exists

A helpdesk measured by a single SLA clock hides the problem: a critical ticket answered in five minutes and resolved in three days counts as success if you only compare ticket age against the resolution deadline. First response and resolution are different measurements and need separate clocks. The queue must also respect severity and wait time, so a serious ticket does not sit behind a minor one. This project was born to measure this with numbers that match the data planted in dados/, covered by tests that recount the seed and compare with the report.

## What it does

- Opens tickets with title, description, category, severity, asset and requester, via the CLI (`abrir`) or `POST /chamados` on the HTTP server.
- Orders the open queue: severity first (critical, high, medium, low), then wait time (oldest first), tie-break by ticket id.
- Measures two SLAs per severity on separate clocks: first response (1 h / 4 h / 8 h / 24 h) and resolution (4x the response deadline: 4 h / 16 h / 32 h / 96 h). A ticket answered quickly and resolved late breaches only the resolution clock.
- Records first response, resolution, agent and solution with date and time.
- Maintains the equipment inventory (code, type, brand, model, location, status) and counts tickets per asset.
- Generates the performance report in Markdown: SLA met by severity (response and resolution), backlog by severity, MTTR and most recurring assets.
- Local HTTP server (`http.server`) on `127.0.0.1` with routes `GET /`, `/fila`, `/chamados/<id>`, `/inventario`, `/relatorio` and `POST /chamados`; no authentication, intended for local use.
- Local SQLite database created from the seeds in `dados/` on first run; an already populated database is never rewritten.

## Stack

- Python 3.10 or higher
- PyYAML >= 6.0 (reading the YAML seeds; the rest is standard library)
- SQLite (single local database file)
- pytest and pytest-cov (dev, optional, to run `tests/`)

## How it works

Ticket cycle: opened → in_progress → resolved. Each ticket stores `criado_em`, `primeira_resposta_em`, `resolvido_em`, `solucao`, agent, category and asset code.

Queue: open tickets come out ordered by (severity weight, `criado_em`, id). `listar` shows open tickets in queue order, followed by closed ones by closing time.

SLA: first response deadlines by severity — critical 1 h, high 4 h, medium 8 h, low 24 h; resolution deadline equal to 4x the response deadline. `violou_resposta` and `violou_resolucao` are separate functions in `src/helpdesk/sla.py`, and the report displays the two blocks one below the other.

By default, the date reference is the largest timestamp present in the database (last event among opening, response and resolution), not the system clock. This way the same database always generates the same report. Use `--referencia` to simulate "now" when necessary.

`garantir_banco` creates the schema and populates from the seed exactly once; if the database already has data, it refuses re-seeding to avoid erasing the history of whoever operated. Each command opens and closes its own SQLite connection; the server opens one connection per request, since `ThreadingHTTPServer` serves on threads and SQLite does not support a shared connection between threads.

The server is created without starting to listen, so tests can come up in a daemon thread and shut down in `try/finally` without blocking the suite or leaving a port open.

## How to run

Requirement: Python 3.10 or higher.

```powershell
# 1. Create environment and install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Run the performance report (creates and populates dados/helpdesk.sqlite from dados/ automatically)
python -m helpdesk relatorio --saida exemplos\relatorio-desempenho.md
```

Command output over the `dados/` seed (deterministic, identical on each run against the same database)

```markdown
# Performance report - helpdesk

- Reference date: 2026-01-19T04:29:29Z
- Tickets in database: 132
- Resolved: 104
- Open in queue (opened + in progress): 28

## Response SLA (time until first response)

| Severity | Evaluated | Within deadline | Breached | % met |
|---|---:|---:|---:|---:|
| critical | 14 | 12 | 2 | 85.7 |
| high | 33 | 21 | 12 | 63.6 |
| medium | 42 | 31 | 11 | 73.8 |
| low | 31 | 21 | 10 | 67.7 |

## Resolution SLA (time from opening to resolution)

| Severity | Evaluated | Within deadline | Breached | % met |
|---|---:|---:|---:|---:|
| critical | 12 | 11 | 1 | 91.7 |
| high | 28 | 18 | 10 | 64.3 |
| medium | 37 | 30 | 7 | 81.1 |
| low | 27 | 19 | 8 | 70.4 |

## Backlog by severity

| Severity | Open | In progress | Total |
|---|---:|---:|---:|
| critical | 1 | 2 | 3 |
| high | 2 | 5 | 7 |
| medium | 3 | 5 | 8 |
| low | 6 | 4 | 10 |
| Total | 12 | 16 | 28 |

- Open already breached in resolution deadline (at reference date): 28

## MTTR (mean time to resolution)

- MTTR: 35.44 h, calculated over 104 resolved tickets.

## Most recurring tickets by asset

| Asset | Type | Tickets |
|---|---|---:|
| SRV-MAIL-01 | Server | 22 |
| SW-CORE-01 | Switch | 18 |
| SRV-AD-01 | Server | 12 |
| VR-001 | Virtual server | 12 |
| PDC-LOJA-05 | PC | 10 |
```

Other commands

```powershell
python -m helpdesk --help
python -m helpdesk listar --limit 8 --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk abrir --titulo "Impressora parada" --descricao "O time não consegue imprimir" `
  --categoria "Hardware" --ativo IMP-F04-01 --solicitante "Ana Duarte" `
  --marca 2026-01-05T09:00:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk responder 133 --marca 2026-01-05T09:40:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk resolver 133 --solucao "Trocou o cartucho" --marca 2026-01-05T11:00:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk inventario
python -m helpdesk inventario --adicionar NB-77 --tipo Laptop --marca Prisma --modelo T14 --local TI
python -m helpdesk relatorio --top 10 --referencia 2026-01-10T00:00:00Z
python -m helpdesk servidor --porta 8471
python tools\gerar_dados.py
```

## Project structure

```
helpdesk.py              shim: python -m helpdesk from the root without installing the package
pyproject.toml           metadata, entry point helpdesk = helpdesk.cli:main and pytest configuration
requirements.txt         PyYAML and dev dependencies (pytest, pytest-cov)
src/helpdesk/
  __init__.py            version 1.0.0
  __main__.py            entry of python -m helpdesk
  modelo.py              Ticket, Usuario, Equipamento and ISO-8601 conversion with Z suffix
  fila.py                queue ordering and agent assignment by lowest load
  sla.py                 deadlines by severity; two clocks (response and resolution)
  banco.py               SQLite, schema, garantir_banco, popular_do_seed, ticket CRUD
  inventario.py          registration, query and ticket count per asset
  relatorio.py           SLA met, backlog, MTTR, recurring assets; deterministic markdown
  servidor.py            local HTTP server (http.server) with JSON routes
  cli.py                 subcommands abrir, listar, responder, resolver, inventario, relatorio, servidor
dados/
  chamados-semente.yaml  10 users and 132 tickets
  inventario-semente.yaml 12 equipment
  catalogo-servicos.yaml categories, default severity per category and teams
  helpdesk.sqlite        generated on run (gitignored)
docs/                    matriz-de-prioridade.md and como-escrever-um-bom-chamado.md
exemplos/                relatorio-desempenho.md (real output of the README command)
tests/                   unit tests (database, cli, queue, inventory, model, report, server, sla)
tools/                   gerar_dados.py (deterministic generator, seed 20260105), verificar_encoding.py, smoke_servidor.py
```

## Trade-offs and decisions

- Two SLA clocks instead of one: first response and resolution are different measurements; a single clock would classify as success a ticket answered in five minutes and resolved in three days (justified in `docs/matriz-de-prioridade.md`).
- Resolution deadline equal to 4x the response deadline: separates the queue from real work time without inventing four arbitrary numbers; changes in one place in `sla.py`, with a test covering the relationship.
- Reference date equal to the last database event, not `datetime.now()`: deterministic report; the same database always produces the same file. `--referencia` exists to simulate "now".
- Database created and seeded once, never rewritten if already populated: preserves the history of whoever operated.
- One SQLite connection per command or request, nothing shared between threads: `ThreadingHTTPServer` serves on threads and a shared connection between threads is an invitation to problems.
- Server created without starting to listen: allows tests to come up in a daemon thread and shut down in `try/finally`.
- Inventory in a separate YAML file from tickets: equipment is a durable entity, not born and dying with the ticket cycle.
- No authentication on the HTTP server: it listens on `127.0.0.1` and lives while the process runs; it is a local tool, not to expose on the network.

## Known limitations

- HTTP server without authentication: do not expose the port.
- SLA measures calendar time, not business hours: it does not stop at midnight or on holidays. Suitable for 24x7 operation (data center), unsuitable for a business-hours helpdesk.
- No transition history: `solucao` is a single text; if the ticket passed through three agents, only the last remains in the database.
- No notification: no email, notification queue or audit; recording and measurement system, not a production helpdesk.
- Single-write SQLite: concurrent writes produce `database is locked`; more than one operator at a time requires another write front.

## License

MIT. See [LICENSE](LICENSE).

## Author

Kelvin Oliveira  
https://github.com/KelvinOliveiraCode  
https://kelvinoliveiracode.github.io/portfolio/
