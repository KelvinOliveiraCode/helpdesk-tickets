# Matriz de prioridade e decisoes de SLA

Este documento e a referencia de leitura para o sistema: como a prioridade e
calculada, por que o SLA tem dois relogios, e as decisoes de infraestrutura
local que valem para quem for estender o projeto.

## A matriz

| Severidade | Resposta (1a resposta) | Resolucao | Exemplo de uso |
|---|---:|---:|---|
| critica | 1 h | 4 h | Servico fora do ar (mail, AD, sistema de vendas) |
| alta | 4 h | 16 h | Perda de rede de uma ala, sistema lento demais |
| media | 8 h | 32 h | Caixa de entrada parada, integracao fora do horario |
| baixa | 24 h | 96 h | Periferico, licenca, ajuste de bancada |

Os valores de resposta sao os da spec do projeto (1h / 4h / 8h / 24h). O
prazo de resolucao e **4x o prazo de resposta**, em todas as severidades.

### Por que 4x e nao um numero unico

Numa operacao pequena, resposta em 10 minutos e resolucao em 2 horas parecem
"o mesmo chamado bom". Na pratica, sao medicos diferentes: o primeiro mede o
tempo ate o suporte assumir o chamado, o segundo mede o tempo ate o usuario
voltar a trabalhar. Usar 4x separa a fila do tempo de trabalho real sem
inventar quatro numeros arbitrarios. Se a sua organizacao tem SLA contratual
diferente, o lugar para mudar e `PRORROS_RESOLUCAO_H` em `src/helpdesk/sla.py`
(tabela em um so lugar, com teste cobrindo a relacao 4x).

## Por que dois relogios separados (e o bug que ficou pra tras)

A primeira versao do relatorio media um relogio unico: idade do chamado
contra o prazo de resolucao. O resultado no seed era um numero de SLA que
"passava" para um chamado critico respondido em 5 minutos e resolvido em 3 dias,
porque a medicao puxava a media para baixo. O bug so apareceu quando escrevi
o teste que confere o MTTR contra o seed a mao: o numero do relatorio e o
numero calculado no teste nao batiam, e a diferenca veio exatamente dos
chamados com resposta rapida e resolucao demorada.

A consequencia: `sla.py` tem `violou_resposta` e `violou_resolucao` como
funcoes separadas, e o relatorio reporta os dois blocos um abaixo do outro.
Nunca mediasse "tempo de atendimento" como se fosse um unico intervalo.

## Como a fila e ordenada

1. Severidade: critica > alta > media > baixa.
2. Tempo de espera: dentro da mesma severidade, o mais antigo sai primeiro.
3. Empate total: id do chamado (nao muda a ordem se dois chamados forem
   abertos no mesmo segundo).

Atribuicao de agente (quando a operacao nao informa): menos chamados abertos
no momento, desempate por ordem alfabetica. O desempate alfabetico foi
decisao consciente: qualquer outra regra "aleatoria" faria o teste de
determinismo do relatorio falhar em execucao alternada.

## O que e "estourado" para aberto

O relatorio marca um aberto como "estourado" quando a data de referencia
passou do prazo de resolucao daquela severidade. A data de referencia **nao
e o relogio do sistema**: por padrao e o ultimo evento presente no banco
(maior entre aberturas, respostas e resolucoes). Duas consequencias:

- o mesmo banco sempre produz o mesmo relatorio (rodar o comando duas vezes,
  em minutos diferentes, nao muda o arquivo), e foi isso que permitiu colar
  saida real no README e no `exemplos/`;
- para simular "agora", existe `relatorio --referencia ISO-8601Z`.

## Banco local: decisoes de arquivo

- O padrao do `--banco` e `dados/helpdesk.sqlite`, relativo ao diretorio de
  onde o comando roda. O arquivo nao entra no repositorio: adicionei
  `*.sqlite` ao `.gitignore` (o template nao cobre SQLite, e o criterio de
  aceite exige que o comando do README funcione a partir do seed sem nenhum
  passo extra). A linha foi somada apos a copia literal do template.
- Se o arquivo nao existe, `garantir_banco` cria o esquema e popula do seed
  uma vez. Se existe mas esta vazio, popula tambem. Se tem dados, **nao**
  reescreve: re-seed de banco populado perderia a historia.
- Todo comando abre e fecha conexao; o servidor abre uma conexao por
  requisicao. SQLite nao gosta de conexao aberta entre threads, e o
  `ThreadingHTTPServer` atende em threads.
- Os seeds ficam em `dados/chamados-semente.yaml` (usuarios + 132 chamados)
  e `dados/inventario-semente.yaml` (12 equipamentos). O inventario fica em
  arquivo separado porque equipamento e entidade duradoura: ele nao nasce e
  morre com o ciclo do chamado, e voce vai querer trocar os chamados do seed
  sem reescrever o inventario (e o contrario). O terceiro arquivo,
  `catalogo-servicos.yaml`, tem categorias, severidade padrao por categoria e
  as equipes; `abrir --categoria X` usa a severidade padrao dele quando
  `--severidade` nao vem.

## Reproducindo o seed

```powershell
python tools\gerar_dados.py
```

O gerador usa so a biblioteca padrao, seed fixo (`20260105`) e escreve os
tres YAMLs em `dados/`. Rodar duas vezes produz bytes identicos (confirmei
com hash de arquivo). Os numeros que os testes conferem (132 chamados,
contagem por severidade, MTTR, top de ativos) saem deste gerador, nao de
edicao manual.
