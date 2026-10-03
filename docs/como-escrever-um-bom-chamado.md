# Como escrever um bom chamado

Este doc e para a pessoa que **abre** o chamado, nao para quem atende.
Cinco minutos de boa descricao economizam horas de ida e volta na fila.

## A anatomia de um chamado util

Um chamado que o atendente consegue resolver sem te ligar de volta tem
sempre estes cinco pedacos:

1. **O que** esta acontecendo (o sintoma, nao o seu palpite sobre a causa);
2. **Quando** comecou (data e hora aproximada; "desde o inicio da semana"
   nao e data);
3. **Onde** (terminal, sala, departamento; e o codigo do ativo, se souber);
4. **Quem e quanto** esta afetado (voce, um time, a operacao inteira);
5. **O que ja foi tentado** (reiniciou? trocou o cabo? mesmo erro?).

O sistema deste repositorio tem um campo para cada um: `titulo`,
`criado_em` (marque com `--marca` quando souber a hora), `ativo`,
`descricao` (quem, quanto e o que ja tentou) e `solucao` (o que resolveu,
para o proximo caso igual).

## Antes / depois: o mesmo problema

### Antes (vago)

```
Titulo:    Impressora
Descricao: nao imprime, ta ruim, resolve
```

O que esse chamado nao diz: qual impressora, desde quando, quem usa, se
reiniciou, se o erro e "papel" ou "off-line". O atendente vai abrir em
`baixa` por padrao, nao achar o ativo, e o chamado fica 24 horas na fila
esperando um telefone seu.

### Depois (util)

```
Titulo:    IMP-F04-01 (Financeiro 4 and) fora do ar desde 07/01 14h
Descricao: Impressora da sala 4 and ta offline desde as 14h de terca.
           O time inteiro de Financeiro ta imprimindo o demonstrativo do
           dia. Reiniciei a impressora e o notebook; mesma mensagem
           "off-line". O arquivo fica parado na fila local do Windows.
```

Mesmo problema, mas agora o atendente ja sabe o ativo (`IMP-F04-01`), a hora
(`07/01 14h`, vira o `criado_em`), o impacto (o time inteiro) e o que ja foi
tentado (reinicio, falhou). Resolve em minutos em vez de dias.

No sistema, isso e:

```powershell
python -m helpdesk abrir `
  --titulo "IMP-F04-01 fora do ar desde 07/01 14h" `
  --descricao "Time inteiro de Financeiro parado. Reiniciei impressora e notebook; segue off-line." `
  --categoria "Hardware" `
  --ativo "IMP-F04-01" `
  --solicitante "seu nome" `
  --marca "2026-01-07T14:05:00Z"
```

## Como escolher a severidade

Use a matriz de `docs/matriz-de-prioridade.md` como regua:

| Situacao | Severidade | Por que |
|---|---|---|
| Servico que para a casa (mail, AD, sistema de vendas) | critica | prazo de resposta: 1 h |
| Perda de rede de uma ala, sistema nao serve | alta | 4 h |
| Caixa de entrada parada, um usuario ou um time lento | media | 8 h |
| Periferico, licenca, ajuste de bancada | baixa | 24 h |

A tentacao mais comum e **superclassificar**: um notebook lento virou
"critica" na pressa. A consequencia aparece no relatorio: o % de SLA de
resposta cai, a fila de critica vira fila de lixo, e o que de verdade e
critico fica atras do seu chamado. Se nao consegue decidir entre duas,
comece na menor; o atendente pode escalar, a fila nao.

## O que atrasa seu chamado na fila

- **Severidade errada para cima**: pula a fila com prioridade que nao tem,
  e depois o time tem que reabrir como "reescalonar" (a gente chama de
  chamado fantasma).
- **Sem codigo de ativo**: o atendente perde o tempo de descobrir qual
  equipamento; `listar --ativo` e o comando que salva esse tempo, mas so
  se o campo estiver preenchido.
- **Sem data/hora**: sem `criado_em` confiavel, o tempo de espera da fila e
  medido errado, e o SLA de resposta comeca a contar do "agora" que o
  atendente abriu, nao do seu problema.
- **"Tentei de tudo" sem especificar**: "reiniciei" e "troquei o SSD" sao
  informacoes diferentes; sem a segunda metade, o atendente refaz o que
  voce ja fez.

## Checklist antes de enviar

1. O titulo diz **o que** e **onde** (ativo, se souber)?
2. A descricao tem **quando**, **quem e quanto** e **o que ja tentei**?
3. A severidade passa no teste do "e a operacao inteira que para"?
4. Se soube a hora em que comecou, marcou com `--marca`?
5. Pode viver dois dias sem falar com voce, que o atendente ainda tem
   tudo que precisa?

Se a resposta for sim para as cinco, o chamado esta pronto.
