# Robô TCE-ES: Painel de Controle (recorte saúde)

> **Situação em 15/10/2026:** extração validada e funcionando. Falta decidir
> onde publicar no site (`montar.py`/`enviar.py`) e o agendamento definitivo.

## O que é

Painel de Controle do Tribunal de Contas do Espírito Santo
(https://paineldecontrole.tcees.tc.br), recorte da área temática **Saúde**.
O site tem 6 painéis de saúde, todos páginas do **mesmo relatório Power BI
"publicar na web"**:

| Página (pageName) | O que mostra |
|---|---|
| (a identificar) | Estabelecimentos de saúde (CNES) |
| (a identificar) | Distribuição de leitos |
| (a identificar) | Distribuição de equipamentos |
| `ReportSection544931c3083d7668ba47` | **Gastos com a função saúde** (implementado) |
| (a identificar) | Planos Municipais de Saúde |
| (a identificar) | Detalhamento dos planos de saúde |

Prioridade e único implementado até agora: **Gastos com a função saúde** —
aplicação por município, valor médio por habitante, gastos por subfunção,
evolução por ano, população com/sem plano de saúde privado (ANS). Complementa
o [[robo]] InvestSUS/FNS (que olha repasses do governo federal): este painel
olha o valor efetivamente aplicado por cada município, fiscalizado pelo TCE-ES.

Identificadores do relatório (mesmos para todas as páginas, só troca o
`pageName`):
- `k` (chave pública do relatório): `0b4992ae-e680-4f0c-b307-83c889f69479`
- `t` (tenant): `9d1437b1-472c-4501-9439-dcfe9a41f2b0`
- `DatasetId`: `f5ebfd6a-e30f-49d3-b934-3eeafab08c8e`
- `ReportId`: `fe419ce5-a6b0-4a69-9186-1842a5b27a10`
- `modelId`: `9177658`

## Como a extração funciona (sem navegador)

O Painel de Controle **não tem API REST própria**. Cada painel temático é um
relatório Power BI "publicar na web" incorporado via iframe
`app.powerbi.com/view?r=<token>&pageName=<página>`.

Testamos (`testar_acesso.py`, via Playwright) e confirmamos que o relatório
carrega normalmente a partir do GitHub Actions e dispara chamadas internas
para `wabi-brazil-south-api.analysis.windows.net/public/reports/querydata`
(infraestrutura Microsoft/Azure, região Brasil — sem bloqueio, diferente do
FNS/INLABS). Analisando o corpo dessas chamadas, descobrimos que:

- A requisição carrega seus **próprios identificadores** (DatasetId, ReportId,
  VisualId, modelId) dentro do corpo — não depende de nada do lado do servidor
  além da chave pública do relatório.
- Os únicos cabeçalhos "especiais" são `x-powerbi-resourcekey` (a chave `k`
  acima, pública) e dois GUIDs de correlação (`requestid`/`activityid`) que o
  **próprio cliente gera livremente** — não são sessão nem cookie.

Ou seja: **a chamada é sem estado e pode ser reenviada via HTTP puro**
(`requests`), sem precisar abrir navegador nenhum. Confirmado em
`testar_replay.py` (reenvio de uma consulta capturada, fora de qualquer
sessão de navegador) e depois em `extrair.py` (reenvio de todas as consultas
relevantes). Isso foi validado contra os números reais mostrados na tela em
15/10/2026 (R$ 3,65 Bi aplicado, R$ 880,38/habitante, 17,63% com plano
privado, 1.416.415 pessoas, ranking por município e por subfunção, evolução
2020–2026) — todos batem.

### Formato da resposta (DSR)

As respostas vêm no formato "DSR" (Data Shape Result) do Power BI, que
comprime linhas repetindo só o que mudou entre uma linha e a seguinte
(bitmasks `R` de repetição e `Ø` de nulo). O decodificador está em `dsr.py`,
testado manualmente contra os números da tela — ver comentários no próprio
arquivo.

## Arquivos

- `consultas/*.json`: corpo exato de cada consulta Power BI capturada (21 ao
  todo — 8 usadas em `extrair.py`, as demais são auxiliares da interface:
  badges HTML, legendas, opções de filtro, min/max do mapa — guardadas de
  referência).
- `dsr.py`: decodificador do formato DSR.
- `extrair.py`: reenvia as 8 consultas relevantes via HTTP puro, decodifica
  e grava um JSON com os dados brutos (ainda não é o formato final do site).
  Aceita um ano de referência opcional (`python extrair.py saida.json 2025`).
- `testar_acesso.py`: teste original via Playwright (navegador) — mantido
  como registro de como a descoberta foi feita e para investigar páginas
  novas do mesmo relatório (basta trocar `PAGE_NAME`).
- `testar_replay.py`: teste de replay via HTTP puro de uma única consulta.

## Próximos passos

1. **Decidir com o Rafael:** pasta de destino no site (`partelli.pro/<área>/`)
   e frequência de atualização.
2. Escrever `montar.py`: transforma a saída de `extrair.py` no JSON final do
   site (padrão parecido com o `dados.json` do robô InvestSUS), com a trava
   de variação (seguir o padrão de 40% usado no InvestSUS) antes de publicar.
3. Escrever `enviar.py` (publicação — FTP ou cópia local, a definir).
4. Rodar manualmente uma vez do jeito de produção, conferir no site, só então
   agendar. Dado que a extração funciona por HTTP puro e sem bloqueio, o
   **GitHub Actions é a primeira opção** (ordem de preferência do
   `CLAUDE.md` raiz) — mais barato e simples que Hostinger ou computador.
5. Se útil, repetir o processo para as outras 5 páginas do mesmo relatório
   (mesmo `k`/`t`/`DatasetId`, só muda `pageName` e as consultas de cada
   página — usar `testar_acesso.py` com o novo `PAGE_NAME` para capturar).

## Segurança

Nenhuma credencial é necessária (o relatório é público, com chave pública de
leitura). Os identificadores acima (`k`, `t`, `DatasetId`, `ReportId`,
`modelId`) não são segredos — são os mesmos embutidos no HTML público do
site do TCE-ES, por isso estão versionados sem problema.
