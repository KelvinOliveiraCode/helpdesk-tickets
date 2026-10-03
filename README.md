<div align="center">

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-82%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-94%25-blue?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/deps-PyYAML%20only-blue?style=flat-square" alt="Deps">
</p>

# helpdesk-tickets

**Chamados, fila, SLA por severidade, inventario e relatorio de desempenho num banco local.**

</div>

---

## PT-BR

### O que e

CLI + servidor HTTP local (http.server) por cima de um SQLite que abre chamados,
ordena a fila por severidade e tempo de espera, mede SLA de resposta e de
resolucao separados, guarda o inventario de equipamentos e emite o relatorio de
desempenho (percentual de SLA, backlog, MTTR e ativos recorrentes). Tudo offline,
com 132 chamados e 12 ativos plantados em `dados/`.

### Por que foi feito

Suporte e o dia a dia de quem entra em TI, e a parte mais vulneravel de um
helpdesk nao e abrir chamado: e dizer **quando** ele foi respondido e
**quando** foi resolvido, separando as duas coisas. Um chamado "respondido em
10 minutos" que ficou 6 dias na fila ate a resolucao nao e um chamado bem
atendido, mas relogio unico de SLA media isso como sucesso. O projeto endereca
a dor de medir isso: a fila tem que respeitar severidade e tempo de espera, o
SLA tem que ter dois relogios, e o numero do relatorio tem que bater com o
dado plantado, com teste provando os dois.

### Como rodar

```powershell
# 1. Instalar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Validar
python -m pytest tests/ -v

# 3. Executar (o banco e criado e populado do seed em dados/ automaticamente)
python -m helpdesk relatorio --saida exemplos\relatorio-desempenho.md
```

Saida real:

```
# Relatorio de desempenho - helpdesk

- Data de referencia: 2026-01-19T04:29:29Z
- Chamados no banco: 132
- Resolvidos: 104
- Abertos na fila (aberto + em atendimento): 28

## SLA de resposta (tempo ate a primeira resposta)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| critica | 14 | 12 | 2 | 85.7 |
| alta | 33 | 21 | 12 | 63.6 |
| media | 42 | 31 | 11 | 73.8 |
| baixa | 31 | 21 | 10 | 67.7 |

## SLA de resolucao (tempo da abertura a resolucao)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| critica | 12 | 11 | 1 | 91.7 |
| alta | 28 | 18 | 10 | 64.3 |
| media | 37 | 30 | 7 | 81.1 |
| baixa | 27 | 19 | 8 | 70.4 |

## Backlog por severidade

| Severidade | Aberto | Em atendimento | Total |
|---|---:|---:|---:|
| critica | 1 | 2 | 3 |
| alta | 2 | 5 | 7 |
| media | 3 | 5 | 8 |
| baixa | 6 | 4 | 10 |
| Total | 12 | 16 | 28 |

- Abertos ja estourados no prazo de resolucao (na data de referencia): 28

## MTTR (tempo medio de resolucao)

- MTTR: 35.44 h, calculado sobre 104 chamados resolvidos.

## Chamados mais recorrentes por ativo

| Ativo | Tipo | Chamados |
|---|---|---:|
| SRV-MAIL-01 | Servidor | 22 |
| SW-CORE-01 | Switch | 18 |
| SRV-AD-01 | Servidor | 12 |
| VR-001 | Servidor Virtual | 12 |
| PDC-LOJA-05 | PC | 10 |


Relatorio salvo em: exemplos\relatorio-desempenho.md / report saved to: exemplos\relatorio-desempenho.md
```

Orelhacao do banco recem-criado (fila em ordem de prioridade):

```powershell
python -m helpdesk --help
```

```
usage: helpdesk [-h] [--versao] COMANDO ...

Sistema local de chamados: abertura, fila, SLA por severidade, inventario e
relatorio de desempenho. Local ticket system: open tickets, queue, SLA per
severity, inventory and performance report.

positional arguments:
  COMANDO
    abrir       abre um chamado / open a ticket
    listar      lista chamados (abertos em ordem de fila) / list tickets (open
                ones in queue order)
    responder   registra a primeira resposta de um chamado / record the first
                answer of a ticket
    resolver    resolve um chamado aberto / resolve an open ticket
    inventario  lista ou cadastra equipamentos / list or register equipment
    relatorio   gera o relatorio de desempenho / generate the performance report
    servidor    sobe o servidor HTTP local / start the local HTTP server

options:
  -h, --help    show this help message and exit
  --versao      show program's version number and exit
```

Ciclo de vida de um chamado na fila real do seed (banco temporario, sem tocar o
`dados/helpdesk.sqlite`):

```powershell
python -m helpdesk listar --limit 8 --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk abrir --titulo "Impressora parada" --descricao "O time nao consegue imprimir" `
  --categoria "Hardware" --ativo IMP-F04-01 --solicitante "Ana Duarte" `
  --marca 2026-01-05T09:00:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk responder 133 --marca 2026-01-05T09:40:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk resolver 133 --solucao "Trocou o cartucho" --marca 2026-01-05T11:00:00Z --banco .\tmp-demo.sqlite --dados dados
```

Saida real do ciclo:

```
ID   SEVERIDADE STATUS         ATIVO          CRIADO                 TITULO
---- ---------- -------------- -------------  ---------------------  ------------------------------
14   critica    aberto         SRV-MAIL-01     2026-01-06T00:15:02Z  Produtividade parada por SRV-MAIL-01
20   critica    em_atendimento TK-012          2026-01-06T08:48:02Z  Caida total: TK-012 inacessivel
24   critica    em_atendimento SW-CORE-01      2026-01-06T11:19:31Z  Caida total: SW-CORE-01 inacessivel
4    alta       em_atendimento MON-OP-02       2026-01-05T12:32:07Z  Periferico de MON-OP-02 cortou o ...
6    alta       aberto         SRV-MAIL-01     2026-01-05T18:53:35Z  Planilha travando no turno da manha
27   alta       em_atendimento VR-001          2026-01-06T16:39:31Z  Integracao de VR-001 fora do horario
30   alta       em_atendimento MON-OP-02       2026-01-06T19:18:46Z  MON-OP-02 nao liga no turno da manha
51   alta       em_atendimento AP-3F-01        2026-01-07T20:23:41Z  Enlace instavel ligado em AP-3F-01

TOTAL: 132 chamado(s) / ticket(s)

Chamado #133 criado / ticket #133 created
  severidade: baixa | categoria: Hardware | ativo: IMP-F04-01
Chamado #133 respondido em 2026-01-05T09:40:00Z por Time B / ticket #133 answered by Time B
Chamado #133 resolvido / ticket #133 resolved
```

Outros comandos:

```powershell
python -m helpdesk inventario                                   # inventario + chamados por ativo
python -m helpdesk inventario --adicionar NB-77 --tipo Laptop --marca Prisma --modelo T14 --local TI
python -m helpdesk relatorio --top 10 --referencia 2026-01-10T00:00:00Z
python -m helpdesk servidor --porta 8471                        # GET /, /fila, /chamados/<id>, /inventario, /relatorio; POST /chamados
python tools\gerar_dados.py                                     # regenera os seeds de dados/ (deterministico, seed 20260105)
```

### O que aprendi

- **SLA e dois relogios, nao um.** A primeira versao media a idade do chamado
  contra o prazo de resolucao so, e o seed me mostrou o erro: critica
  respondida em 5 minutos e resolvida em 3 dias "passava" no relogio unico. O
  bug quebrou o teste que confere o MTTR contra o seed calculado a mao. A
  consequencia morou em `sla.py` (`violou_resposta` e `violou_resolucao`
  separadas) e no relatorio, que reporta os dois blocos.
- **Data de referencia = ultimo evento do banco, nao o relogio.** Com
  `datetime.now()`, dois `relatorio` rodados em minutos diferentes nao batiam,
  e eu nao tinha como colar saida real no README. Trocar por "maximo dos
  timestamps do banco" deu determinismo sem achar o relagor de producao;
  `--referencia` existiu para simular "agora" quando isso importa.
- **Banco padrao gitignored + seed so uma vez.** O `--banco` default em
  `dados/helpdesk.sqlite` fez o comando do README funcionar direto apos o
  clone; o `.gitignore` ganhou `*.sqlite` (fora do template) para isso.
  `garantir_banco` popula banco ausente ou vazio, e rejeita re-seed de banco
  ja populado - porque reescrever o seed perderia a historia de quem operou.
- **Servidor em teste: porta 0, thread daemon, shutdown em finally.**
  `serve_forever` bloqueia; o teste sobe o servidor numa porta livre em
  thread daemon e derruba com `shutdown` + `server_close` em `try/finally`,
  senao a suíte trava ou deixa porta aberta. E cada requisicao abre e fecha
  sua conexao SQLite: compartilhar conexao entre threads de
  `ThreadingHTTPServer` e pedido de falha.
- **Seed por gerador, dados conferidos por contagem exata.** Nada de YAML
  escrito a mao: `tools/gerar_dados.py` (so stdlib, seed `20260105`) materializa
  os 132 chamados com contagem fixa por severidade (15/35/45/37), 120 com
  resposta, 104 resolvidos, 26 estourados por relogio e dois ativos
  claramente recorrentes (SRV-MAIL-01: 22, SW-CORE-01: 18). Os testes
  recontam tudo a partir do YAML e comparam com o relatorio - e e isso que
  prova que o numero do relatorio vem dos dados, nao do codigo.

### Limitacoes

- **O servidor HTTP nao tem autenticacao.** E ferramenta local: ele escuta em
  `127.0.0.1` e so existe enquanto o processo vive. Nao exponha essa porta.
- **SLA mede em hora calendaria, nao em hora de expediente.** O relogio nao
  para a meia-noite nem no feriado; para negocio 24x7 (data center), isso e
  correto; para helpdesk de escritorio, nao e.
- **Sem historico de transicoes.** O campo `solucao` e um texto unico; se o
  chamado andou por tres agentes, so o ultimo fica no banco.
- **Nao notifica nada.** Nao tem e-mail, nao tem fila de notificacao, nao tem
  auditoria; e um sistema de registro e medicao, nao um helpdesk de producao.
- **SQLite de escrita unica.** Concorrencia de escrita vira `database is
  locked`; para mais de um operario simultaneo, a frente de escrita precisa
  trocar.

### Licenca

MIT. Ver [LICENSE](LICENSE).

---

## EN

### What it is

A CLI plus a local HTTP server (http.server) on top of a SQLite database that
opens tickets, orders the queue by severity and waiting time, measures response
SLA and resolution SLA on two separate clocks, keeps the equipment inventory,
and emits the performance report (SLA attainment, backlog, MTTR and recurring
assets). All offline, with 132 tickets and 12 assets planted in `dados/`.

### Why it was built

Support is the day-to-day of anyone working in IT, and the most fragile part
of a helpdesk is not opening tickets: it is saying **when** a ticket was
answered and **when** it was resolved, as two different measurements. A ticket
"answered in 10 minutes" that sat for 6 days until resolution is not a well
served ticket, but a single SLA clock would average that as a success. The
project addresses that measuring pain: the queue must respect severity and
waiting time, the SLA must have two clocks, and the report numbers must match
the planted data, with a test proving both.

### How to run

```powershell
# 1. Install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Validate
python -m pytest tests/ -v

# 3. Run (the database is created and seeded from dados/ automatically)
python -m helpdesk relatorio --saida exemplos\relatorio-desempenho.md
```

Real output:

```
# Relatorio de desempenho - helpdesk

- Data de referencia: 2026-01-19T04:29:29Z
- Chamados no banco: 132
- Resolvidos: 104
- Abertos na fila (aberto + em atendimento): 28

## SLA de resposta (tempo ate a primeira resposta)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| critica | 14 | 12 | 2 | 85.7 |
| alta | 33 | 21 | 12 | 63.6 |
| media | 42 | 31 | 11 | 73.8 |
| baixa | 31 | 21 | 10 | 67.7 |

## SLA de resolucao (tempo da abertura a resolucao)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| critica | 12 | 11 | 1 | 91.7 |
| alta | 28 | 18 | 10 | 64.3 |
| media | 37 | 30 | 7 | 81.1 |
| baixa | 27 | 19 | 8 | 70.4 |

## Backlog por severidade

| Severidade | Aberto | Em atendimento | Total |
|---|---:|---:|---:|
| critica | 1 | 2 | 3 |
| alta | 2 | 5 | 7 |
| media | 3 | 5 | 8 |
| baixa | 6 | 4 | 10 |
| Total | 12 | 16 | 28 |

- Abertos ja estourados no prazo de resolucao (na data de referencia): 28

## MTTR (tempo medio de resolucao)

- MTTR: 35.44 h, calculado sobre 104 chamados resolvidos.

## Chamados mais recorrentes por ativo

| Ativo | Tipo | Chamados |
|---|---|---:|
| SRV-MAIL-01 | Servidor | 22 |
| SW-CORE-01 | Switch | 18 |
| SRV-AD-01 | Servidor | 12 |
| VR-001 | Servidor Virtual | 12 |
| PDC-LOJA-05 | PC | 10 |


Relatorio salvo em: exemplos\relatorio-desempenho.md / report saved to: exemplos\relatorio-desempenho.md
```

First look at the freshly created database (queue in priority order):

```powershell
python -m helpdesk --help
```

```
usage: helpdesk [-h] [--versao] COMANDO ...

Sistema local de chamados: abertura, fila, SLA por severidade, inventario e
relatorio de desempenho. Local ticket system: open tickets, queue, SLA per
severity, inventory and performance report.

positional arguments:
  COMANDO
    abrir       abre um chamado / open a ticket
    listar      lista chamados (abertos em ordem de fila) / list tickets (open
                ones in queue order)
    responder   registra a primeira resposta de um chamado / record the first
                answer of a ticket
    resolver    resolve um chamado aberto / resolve an open ticket
    inventario  lista ou cadastra equipamentos / list or register equipment
    relatorio   gera o relatorio de desempenho / generate the performance report
    servidor    sobe o servidor HTTP local / start the local HTTP server

options:
  -h, --help    show this help message and exit
  --versao      show program's version number and exit
```

Life cycle of one ticket on the real seeded queue (temporary database, the
`dados/helpdesk.sqlite` stays untouched):

```powershell
python -m helpdesk listar --limit 8 --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk abrir --titulo "Impressora parada" --descricao "O time nao consegue imprimir" `
  --categoria "Hardware" --ativo IMP-F04-01 --solicitante "Ana Duarte" `
  --marca 2026-01-05T09:00:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk responder 133 --marca 2026-01-05T09:40:00Z --banco .\tmp-demo.sqlite --dados dados
python -m helpdesk resolver 133 --solucao "Trocou o cartucho" --marca 2026-01-05T11:00:00Z --banco .\tmp-demo.sqlite --dados dados
```

Real output of that cycle:

```
ID   SEVERIDADE STATUS         ATIVO          CRIADO                 TITULO
---- ---------- -------------- -------------  ---------------------  ------------------------------
14   critica    aberto         SRV-MAIL-01     2026-01-06T00:15:02Z  Produtividade parada por SRV-MAIL-01
20   critica    em_atendimento TK-012          2026-01-06T08:48:02Z  Caida total: TK-012 inacessivel
24   critica    em_atendimento SW-CORE-01      2026-01-06T11:19:31Z  Caida total: SW-CORE-01 inacessivel
4    alta       em_atendimento MON-OP-02       2026-01-05T12:32:07Z  Periferico de MON-OP-02 cortou o ...
6    alta       aberto         SRV-MAIL-01     2026-01-05T18:53:35Z  Planilha travando no turno da manha
27   alta       em_atendimento VR-001          2026-01-06T16:39:31Z  Integracao de VR-001 fora do horario
30   alta       em_atendimento MON-OP-02       2026-01-06T19:18:46Z  MON-OP-02 nao liga no turno da manha
51   alta       em_atendimento AP-3F-01        2026-01-07T20:23:41Z  Enlace instavel ligado em AP-3F-01

TOTAL: 132 chamado(s) / ticket(s)

Chamado #133 criado / ticket #133 created
  severidade: baixa | categoria: Hardware | ativo: IMP-F04-01
Chamado #133 respondido em 2026-01-05T09:40:00Z por Time B / ticket #133 answered by Time B
Chamado #133 resolvido / ticket #133 resolved
```

Other commands:

```powershell
python -m helpdesk inventario
python -m helpdesk inventario --adicionar NB-77 --tipo Laptop --marca Prisma --modelo T14 --local TI
python -m helpdesk relatorio --top 10 --referencia 2026-01-10T00:00:00Z
python -m helpdesk servidor --porta 8471
python tools\gerar_dados.py
```

### What I learned

- **SLA is two clocks, not one.** The first version measured ticket age
  against the resolution deadline only, and the seed exposed the mistake: a
  critical ticket answered in 5 minutes and resolved in 3 days "passed" the
  single clock. The bug broke the test that checks MTTR against the seed
  computed by hand. The fix lives in `sla.py` (`violou_resposta` and
  `violou_resolucao` apart) and in the report, which shows both blocks.
- **Reference date = last event in the database, not the wall clock.** With
  `datetime.now()`, two `relatorio` runs minutes apart did not match, and I
  could not paste real output into the README. Replacing it with "the maximum
  timestamp in the database" made the output deterministic without reaching
  for a production clock; `--referencia` exists to simulate "now" when it
  matters.
- **A gitignored default database + one-time seed.** The default `--banco` at
  `dados/helpdesk.sqlite` makes the README command work right after a clone;
  `.gitignore` gained `*.sqlite` (outside the template) for that.
  `garantir_banco` seeds a missing or empty database and refuses to re-seed a
  populated one - because re-seeding would erase the history of who operated
  on it.
- **Server in tests: port 0, daemon thread, shutdown in finally.**
  `serve_forever` blocks; the test starts the server on a free port in a
  daemon thread and tears it down with `shutdown` + `server_close` in
  `try/finally`, otherwise the suite hangs or leaves a port open. And every
  request opens and closes its own SQLite connection: sharing a connection
  across `ThreadingHTTPServer` threads is an invitation to failure.
- **Seed by generator, data checked by exact counts.** No hand-written YAML:
  `tools/gerar_dados.py` (stdlib only, seed `20260105`) materializes the 132
  tickets with a fixed count per severity (15/35/45/37), 120 answered, 104
  resolved, 26 breaking each clock, and two clearly recurring assets
  (SRV-MAIL-01: 22, SW-CORE-01: 18). The tests recount everything from the
  YAML and compare it to the report - that is what proves the report numbers
  come from the data, not from the code.

### Limitations

- **The HTTP server has no authentication.** It is a local tool: it listens on
  `127.0.0.1` and only exists while the process lives. Do not expose this
  port.
- **SLA measures calendar hours, not business hours.** The clock does not
  stop at midnight or on holidays; for a 24x7 operation (data center) that is
  right; for a desktop helpdesk, it is not.
- **No transition history.** The `solucao` field is a single text; if a ticket
  went through three agents, only the last one is kept in the database.
- **It notifies nothing.** No mail, no notification queue, no audit; it is a
  registration and measuring system, not a production helpdesk.
- **Single-writer SQLite.** Concurrent writes become `database is locked`; for
  more than one operator at a time, the write front needs to change.

### License

MIT. See [LICENSE](LICENSE).

---

## Estrutura / Structure

```
helpdesk.py                 shim: python -m helpdesk a partir da raiz sem instalar /
                            lets python -m helpdesk run from the root without install
src/helpdesk/
  modelo.py                 Ticket, Usuario, Equipamento
  fila.py                   ordenacao da fila e atribuicao de agente
  sla.py                    prazos por severidade (resposta e resolucao separadas)
  inventario.py             registro, consulta e contagem por ativo
  banco.py                  SQLite + populacao do seed
  relatorio.py              SLA atingido, backlog, MTTR, ativos recorrentes
  servidor.py               HTTP local (http.server)
  cli.py                    subcomandos abrir/listar/responder/resolver/inventario/relatorio/servidor
dados/                      seeds: 132 chamados, 12 equipamentos, catalogo
docs/                       matriz de prioridade + como escrever um bom chamado
exemplos/                   saida real gerada pelo comando do README
tools/                      gerador deterministico dos seeds (+ smoke do servidor)
tests/                      82 testes (modelo, fila, sla, inventario, banco, relatorio, cli, servidor)
```

## Licenca / License

MIT &mdash; [LICENSE](LICENSE)

---

<div align="center">
  <sub>Por <a href="https://github.com/KelvinOliveiraCode">Kelvin Oliveira</a> &middot;
  <a href="https://kelvinoliveiracode.github.io/portfolio/">portfolio</a></sub>
</div>
