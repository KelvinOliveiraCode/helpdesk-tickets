<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">

# helpdesk-tickets

CLI local e servidor HTTP sobre SQLite que abre chamados, ordena a fila por severidade e tempo de espera, mede SLA de resposta e resolucao em relogios separados, mantem o inventario de equipamentos e emite o relatorio de desempenho.

## Problema / Por que existe

Um helpdesk medido por um unico relogio de SLA mascara o problema: um chamado critico respondido em cinco minutos e resolvido em tres dias conta como sucesso se voce so compara a idade do chamado com o prazo de resolucao. Primeira resposta e resolucao são medições diferentes e precisam de relógios separados. A fila também precisa respeitar severidade e tempo de espera, caso chamado grave fique atrás de chamado leve. Este projeto nasceu para medir isso com números que batem com os dados plantados em dados/, coberto por testes que recontam o seed e comparam com o relatório.

## O que faz

- Abre chamados com título, descrição, categoria, severidade, ativo e solicitante, pela CLI (`abrir`) ou por `POST /chamados` no servidor HTTP.
- Ordena a fila aberta: severidade primeiro (crítica, alta, média, baixa), depois tempo de espera (mais antigo primeiro), desempate pelo id do chamado.
- Mede dois SLAs por severidade em relógios separados: primeira resposta (1 h / 4 h / 8 h / 24 h) e resolução (4x o prazo de resposta: 4 h / 16 h / 32 h / 96 h). Um chamado respondido depressa e resolvido tarde estoura apenas o relógio de resolução.
- Registra primeira resposta, resolução, agente e solução com data e hora.
- Mantém o inventário de equipamentos (código, tipo, marca, modelo, local, status) e conta chamados por ativo.
- Gera o relatório de desempenho em Markdown: SLA atingido por severidade (resposta e resolução), backlog por severidade, MTTR e ativos mais recorrentes.
- Servidor HTTP local (`http.server`) em `127.0.0.1` com rotas `GET /`, `/fila`, `/chamados/<id>`, `/inventario`, `/relatorio` e `POST /chamados`; sem autenticação, destinado a uso local.
- Banco SQLite local criado a partir dos seeds de `dados/` na primeira execução; banco já populado nunca é reescrito.

## Stack

- Python 3.10 ou superior
- PyYAML >= 6.0 (leitura dos seeds YAML; o restante é biblioteca padrão)
- SQLite (arquivo único de banco local)
- pytest e pytest-cov (dev, opcional, para executar `tests/`)

## Como funciona

Ciclo do chamado: aberto → em_atendimento → resolvido. Cada chamado guarda `criado_em`, `primeira_resposta_em`, `resolvido_em`, `solucao`, agente, categoria e código do ativo.

Fila: chamados abertos saem ordenados por (peso da severidade, `criado_em`, id). `listar` mostra os abertos em ordem de fila, seguidos dos fechados por horário de encerramento.

SLA: prazos de primeira resposta por severidade — crítica 1 h, alta 4 h, média 8 h, baixa 24 h; prazo de resolução igual a 4x o de resposta. `violou_resposta` e `violou_resolucao` são funções separadas em `src/helpdesk/sla.py`, e o relatório exibe os dois blocos um abaixo do outro.

Referência de data: por padrão é o maior timestamp presente no banco (último evento entre abertura, resposta e resolução), não o relógio do sistema. Assim o mesmo banco gera sempre o mesmo relatório. Use `--referencia` para simular "agora" quando necessário.

Banco: `garantir_banco` cria o esquema e popula do seed exatamente uma vez; se o banco já tem dados, recusa o re-seed para não apagar o histórico de quem operou. Todo comando abre e fecha sua própria conexão SQLite; o servidor abre uma conexão por requisição, pois `ThreadingHTTPServer` atende em threads e SQLite não suporta conexão compartilhada entre threads.

Servidor: criado sem começar a escutar, para que testes subam em thread daemon e desliguem em `try/finally` sem travar a suíte nem deixar porta aberta.

## Como rodar

Requisito: Python 3.10 ou superior.

```powershell
# 1. Criar ambiente e instalar dependências
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Executar o relatório de desempenho (cria e popula dados/helpdesk.sqlite a partir de dados/ automaticamente)
python -m helpdesk relatorio --saida exemplos\relatorio-desempenho.md
```

Saída do comando sobre o seed de `dados/` (determinística, idêntica a cada execução sobre o mesmo banco)

```markdown
# Relatório de desempenho - helpdesk

- Data de referência: 2026-01-19T04:29:29Z
- Chamados no banco: 132
- Resolvidos: 104
- Abertos na fila (aberto + em atendimento): 28

## SLA de resposta (tempo até a primeira resposta)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| crítica | 14 | 12 | 2 | 85.7 |
| alta | 33 | 21 | 12 | 63.6 |
| média | 42 | 31 | 11 | 73.8 |
| baixa | 31 | 21 | 10 | 67.7 |

## SLA de resolução (tempo da abertura à resolução)

| Severidade | Avaliados | Dentro do prazo | Estourados | % atingido |
|---|---:|---:|---:|---:|
| crítica | 12 | 11 | 1 | 91.7 |
| alta | 28 | 18 | 10 | 64.3 |
| média | 37 | 30 | 7 | 81.1 |
| baixa | 27 | 19 | 8 | 70.4 |

## Backlog por severidade

| Severidade | Aberto | Em atendimento | Total |
|---|---:|---:|---:|
| crítica | 1 | 2 | 3 |
| alta | 2 | 5 | 7 |
| média | 3 | 5 | 8 |
| baixa | 6 | 4 | 10 |
| Total | 12 | 16 | 28 |

- Abertos já estourados no prazo de resolução (na data de referência): 28

## MTTR (tempo médio de resolução)

- MTTR: 35.44 h, calculado sobre 104 chamados resolvidos.

## Chamados mais recorrentes por ativo

| Ativo | Tipo | Chamados |
|---|---|---:|
| SRV-MAIL-01 | Servidor | 22 |
| SW-CORE-01 | Switch | 18 |
| SRV-AD-01 | Servidor | 12 |
| VR-001 | Servidor Virtual | 12 |
| PDC-LOJA-05 | PC | 10 |
```

Outros comandos

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

## Estrutura do projeto

```
helpdesk.py              shim: python -m helpdesk a partir da raiz sem instalar o pacote
pyproject.toml           metadata, ponto de entrada helpdesk = helpdesk.cli:main e configuracao do pytest
requirements.txt         PyYAML e dependencias de dev (pytest, pytest-cov)
src/helpdesk/
  __init__.py            versao 1.0.0
  __main__.py            entrada de python -m helpdesk
  modelo.py              Ticket, Usuario, Equipamento e conversao ISO-8601 com sufixo Z
  fila.py                ordenacao da fila e atribuicao de agente por menor carga
  sla.py                 prazos por severidade; dois relogios (resposta e resolucao)
  banco.py               SQLite, esquema, garantir_banco, popular_do_seed, CRUD de chamados
  inventario.py          registro, consulta e contagem de chamados por ativo
  relatorio.py           SLA atingido, backlog, MTTR, ativos recorrentes; markdown deterministico
  servidor.py            servidor HTTP local (http.server) com rotas JSON
  cli.py                 subcomandos abrir, listar, responder, resolver, inventario, relatorio, servidor
dados/
  chamados-semente.yaml  10 usuarios e 132 chamados
  inventario-semente.yaml 12 equipamentos
  catalogo-servicos.yaml categorias, severidade padrao por categoria e equipes
  helpdesk.sqlite        gerado na execucao (gitignorado)
docs/                    matriz-de-prioridade.md e como-escrever-um-bom-chamado.md
exemplos/                relatorio-desempenho.md (saida real do comando do README)
tests/                   testes de unidade (banco, cli, fila, inventario, modelo, relatorio, servidor, sla)
tools/                   gerar_dados.py (gerador deterministico, seed 20260105), verificar_encoding.py, smoke_servidor.py
```

## Trade-offs e decisões

- Dois relógios de SLA em vez de um: primeira resposta e resolução são medições diferentes; um único relógio classificaria como sucesso um chamado respondido em cinco minutos e resolvido em três dias (justificado em `docs/matriz-de-prioridade.md`).
- Prazo de resolução igual a 4x o prazo de resposta: separa a fila do tempo de trabalho real sem inventar quatro números arbitrários; muda em um só lugar em `sla.py`, com teste cobrindo a relação.
- Data de referência igual ao último evento do banco, não `datetime.now()`: relatório determinístico; o mesmo banco produz sempre o mesmo arquivo. `--referencia` existe para simular "agora".
- Banco criado e semeado uma vez, nunca reescrito se já populado: preserva o histórico de quem operou.
- Uma conexão SQLite por comando ou requisição, nada compartilhado entre threads: `ThreadingHTTPServer` atende em threads e conexão compartilhada entre threads é um convite para problemas.
- Servidor criado sem começar a escutar: permite testes subir em thread daemon e desligar em `try/finally`.
- Inventário em arquivo YAML separado dos chamados: equipamento é entidade duradoura, não nasce e morre com o ciclo do chamado.
- Sem autenticação no servidor HTTP: escuta em `127.0.0.1` e vive enquanto o processo roda; é ferramenta local, não para expor na rede.

## Limitações conhecidas

- Servidor HTTP sem autenticação: não exponha a porta.
- SLA mede hora de calendário, não hora de expediente: não para à meia-noite nem em feriado. Adequado para operação 24x7 (data center), inadequado para helpdesk de expediente.
- Sem histórico de transições: `solucao` é um texto único; se o chamado passou por três agentes, fica só o último no banco.
- Sem notificação: sem e-mail, fila de notificação ou auditoria; sistema de registro e medição, não helpdesk de produção.
- SQLite de escrita única: escrita concorrente gera `database is locked`; mais de um operador ao mesmo tempo requer outra frente de escrita.

## Licença

MIT. Ver [LICENSE](LICENSE).

## Autor

Kelvin Oliveira  
https://github.com/KelvinOliveiraCode  
https://kelvinoliveiracode.github.io/portfolio/
