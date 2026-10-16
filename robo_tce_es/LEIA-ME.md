# Robô TCE-ES: Painel de Controle (recorte saúde)

> **Situação em 16/10/2026:** completo, testado de ponta a ponta e
> publicando de verdade, agora com **duas fontes de dados**. Pipeline
> (`extrair.py` → `montar.py` → `enviar.py`) rodou com sucesso no GitHub
> Actions, com os segredos `FTP_HOST`/`FTP_USUARIO`/`FTP_SENHA` já
> cadastrados neste repositório (Settings → Secrets and variables →
> Actions). Publica em **partelli.pro/tce** (schema `meta`/`es`/
> `subfuncoes`/`m`, confirmado direto no servidor), com
> `dados_anterior.json` preservado a cada envio. Agendado em
> `.github/workflows/robo_tce_es.yml` para segunda, quarta e sexta às
> 06:30 Brasília — primeira opção porque a extração funciona por HTTP
> puro, sem navegador e sem bloqueio de IP (ver seção abaixo), e segue a
> ordem de preferência do `CLAUDE.md` raiz.
>
> **Migração de 16/10/2026:** além das consultas Power BI já existentes,
> `extrair.py` passou a buscar também o indicador oficial de **limite
> constitucional de aplicação em saúde** (EC 29/2000, LC 141/2012 — mínimo
> de 15% da receita) direto da **API REST própria** do Painel de Controle
> (`paineldecontrole.tcees.tc.br/api`), descoberta ao explorar a página
> pública `/municipio/<ano>/<cidade>/gestaoFiscal/saude` que o Rafael
> indicou como modelo. Essa API é mais simples que o Power BI (JSON
> direto, sem decodificação DSR) e traz exatamente o dado de receita que
> não existia nas consultas Power BI desta página — testada e confirmada
> acessível de IP de nuvem compartilhada (GitHub Actions) em 16/10/2026.
> A página (`site/tce/index.html`) ganhou uma nova seção "Limite
> constitucional" com o percentual atual (ES e por município), selo de
> conformidade e comparação entre os 78 municípios com linha de
> referência nos 15%.
>
> **Pedido do Rafael em 15–16/10/2026:** filtro por município, período em
> análise, mínimo/máximo valor por habitante, percentual aplicado por
> município, cards explicados, evolução por ano reativa ao filtro e o
> indicador de limite constitucional de 15% foram implementados.
> **Gestão estadual** foi testada e não é possível com o dataset Power BI
> desta página: a tabela de fatos só registra lançamento por município,
> sem linha de gasto estadual direto (ver nota em `extrair.py`).
> **Estabelecimentos de saúde** ainda não foi feito: é uma página
> diferente do mesmo relatório Power BI (CNES), exige descoberta própria
> (como a feita para esta página) — ver "Próximos passos".

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

## Como a extração do limite constitucional funciona (API REST própria)

O **mesmo site** `paineldecontrole.tcees.tc.br` também tem páginas fora do
relatório Power BI, como `/municipio/<ano>/<cidade>/gestaoFiscal/saude`
("Limites com saúde"), que consomem uma **API REST própria** do TCE-ES
(`/api/...`), bem mais simples que o Power BI:

- `GET /api/Settings/GetAll` → inclui `esferasAdministrativas`, a lista dos
  78 municípios do ES com o id usado nas demais chamadas
  (`idEsferaAdministrativa`). Capturada uma vez e versionada em
  `municipios_tce_es.json` (não muda, não precisa reconsultar a cada
  execução).
- `GET /api/MunicipioControllers/Saude/GetSumario?anoExercicio=<ano>&idEsferaAdministrativa=<id>`
  → `aplicacao`, `aplicacaoPercentual` (percentual da receita aplicado —
  **o indicador oficial do limite de 15%**), `aplicacaoPerCapita`,
  `rankingMunicipal`, por município.
- `GET /api/MunicipioControllers/Saude/GetGraficosEvolucaoAnualAplicacao?idEsferaAdministrativa=<id>&anoExercicio=<ano>`
  → evolução anual (valor e percentual) desde 2022, por município.
- `GET /api/EstadoControllers/Saude/GetSumario?anoExercicio=<ano>` →
  o mesmo indicador agregado para o Espírito Santo inteiro.

Não depende de sessão, cookie ou token dinâmico — só os parâmetros na URL.
Testada e confirmada acessível de IP de nuvem compartilhada (GitHub
Actions, `teste_api_rest_tce_es.yml`) em 16/10/2026. Essa API **não
existia nas consultas Power BI já capturadas** desta página, que não têm
nenhum campo de receita — por isso os dois pedidos do Rafael de
"percentual de recursos próprios" e "limite de 15%" ficaram sem resposta
até essa descoberta.

## Arquivos

- `consultas/*.json`: corpo exato de cada consulta Power BI capturada (22 ao
  todo — 10 usadas em `extrair.py`, as demais são auxiliares da interface:
  badges HTML, legendas, opções de filtro, min/max do mapa — guardadas de
  referência). `gestao_estadual.json` não foi capturada da interface, foi
  derivada de `mapa_aplicacao_por_municipio.json` para testar se dava para
  trazer o gasto estadual — voltou vazia (ver nota em `extrair.py`).
- `dsr.py`: decodificador do formato DSR.
- `municipios_tce_es.json`: lista estável dos 78 municípios do ES com o id
  usado pela API REST (`idEsferaAdministrativa`), capturada de
  `api/Settings/GetAll` em 16/10/2026.
- `extrair.py`: reenvia as consultas Power BI relevantes via HTTP puro,
  decodifica, **e também** busca o indicador de limite constitucional de
  cada um dos 78 municípios e do ES na API REST própria (ver seção acima),
  gravando tudo num único JSON com os dados brutos (ainda não é o formato
  final do site). Aceita um ano de referência opcional
  (`python extrair.py saida.json 2025`).
- `testar_api_rest.py`: teste de acesso isolado à API REST (usado para
  confirmar que respondia de IP de nuvem antes de integrar a produção).
- `montar.py`: transforma a saída de `extrair.py` no `dados.json` final da
  página (`meta`, `es` com os KPIs, a série `evolucao` por ano e
  `limiteConstitucional` (percentual, aplicação, per capita e população do
  ES), `subfuncoes` com valor e variação, `m` com os 78 municípios — valor
  por habitante, variação, população, cobertura de plano de saúde privado,
  `limitePercentual` e `limiteEvolucao` por município). Degradação
  graciosa: se a API REST falhar numa execução, esses campos ficam `null`
  e o resto do pipeline publica normalmente. Valida (`validar()`) antes de
  gravar: aplicação e valor por habitante positivos, percentual com plano
  entre 0 e 1, pelo menos 70 municípios.
- `enviar.py`: publica `dados.json` em `partelli.pro/tce` por FTP(S), nos
  mesmos moldes do `robo/enviar.py` (guarda a versão anterior como
  `dados_anterior.json`). Credenciais em `~/.config/robo_tce_es/.env`
  (modelo em `.env.exemplo`).
- `robo.sh`: encadeia `extrair.py` → `montar.py` → trava de variação (40%,
  comparando com `saida/publicado.json`) → `enviar.py`. Para uso no
  computador ou Hostinger, se um dia for preciso trocar de GitHub Actions.
- `testar_acesso.py`: teste original via Playwright (navegador) — mantido
  como registro de como a descoberta foi feita e para investigar páginas
  novas do mesmo relatório (basta trocar `PAGE_NAME`).
- `testar_replay.py`: teste de replay via HTTP puro de uma única consulta.

## Página publicada

`partelli.pro/tce` (arquivos em `site/tce/` neste repositório):
KPIs (aplicação total do ES, valor médio por habitante, menor e maior valor
por habitante com o município, população com plano de saúde privado),
selo com o período em análise (mês inicial/final do ano, já que o ano mais
recente costuma estar parcial), gráfico de evolução por ano com variação,
gasto por subfunção, ranking dos 78 municípios (ordenável, buscável,
clicável, com valor aplicado em R$ e percentual sobre o total do ES) e
leitura estratégica com recomendações — mesmos componentes visuais e mesma
lógica de filtro por ente do Radar de Recursos SUS (`/gestor/recursos/`),
para manter a mesma experiência entre as páginas de dados do site. Tem
também um cartão na Área do Gestor (`/gestor/`) com os KPIs principais.

Desde 16/10/2026, inclui também a seção **"Limite constitucional de
aplicação em saúde"**: um indicador em formato de velocímetro com o
percentual da receita aplicado em saúde (ES ou do município selecionado),
selo "Acima"/"Abaixo" do mínimo de 15% exigido pela EC 29/2000 e LC
141/2012, e uma lista comparativa dos 78 municípios ordenada do maior para
o menor percentual, com linha de referência nos 15%. A tabela de
municípios ganhou uma coluna com esse percentual, e os alertas e a leitura
estratégica agora citam nominalmente os municípios abaixo do limite
mínimo. Modelo de referência usado nesta seção: página oficial do TCE-ES
em `paineldecontrole.tcees.tc.br/municipio/<ano>/<município>/gestaoFiscal/saude`.

## Próximos passos

1. **Estabelecimentos de saúde (CNES):** página diferente do mesmo
   relatório Power BI do TCE-ES. Para implementar, repetir o processo de
   descoberta feito para esta página (usar `testar_acesso.py` com o
   `pageName` certo — falta identificar qual dos 6 é o de estabelecimentos,
   listados no topo deste arquivo) e depois seguir o mesmo padrão
   extrair/montar/enviar.
2. Rodar o agendamento por algumas semanas e conferir se a trava de 40%
   nunca dispara por engano (troca de ano em janeiro, por exemplo) — isso
   agora vale tanto para os dados do Power BI quanto para a API REST do
   limite constitucional.
3. Se útil, repetir o processo também para as demais páginas do mesmo
   relatório (Distribuição de leitos, Distribuição de equipamentos, Planos
   Municipais de Saúde, Detalhamento dos planos de saúde).
4. **Arrecadação total em R$ (não só o percentual):** a API REST usada
   para o limite constitucional só expõe o percentual já calculado, não a
   receita bruta do município. Se o Rafael quiser esse valor em reais,
   investigar a página "Comparação de Municípios" do mesmo painel
   (`paineldecontrole.tcees.tc.br`), que parece trazer a composição da
   receita arrecadada.

## Segurança

Nenhuma credencial é necessária (o relatório é público, com chave pública de
leitura). Os identificadores acima (`k`, `t`, `DatasetId`, `ReportId`,
`modelId`) não são segredos — são os mesmos embutidos no HTML público do
site do TCE-ES, por isso estão versionados sem problema.
