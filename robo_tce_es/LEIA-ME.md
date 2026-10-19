# Robô TCE-ES: Painel de Controle (recorte saúde)

> **Atualização em 19/10/2026 — série histórica de 8 anos:** a pedido do
> Rafael ("transportar para o robô todas as informações da API, usando
> nosso modelo de site para leitura mais dinâmica, com série histórica de
> 8 anos a contar de hoje"), `extrair.py` passou a chamar
> `GetSumario` da API REST própria **uma vez por ano, para os últimos 8
> anos (hoje: 2019-2026)**, para o ES e para cada um dos 78 municípios —
> em vez de só o ano mais recente. Testamos antes (`testar_historico.py`,
> resultado em `resultados/teste-historico-tce-es.json`) e confirmamos
> que `GetSumario` tem dado real desde pelo menos 2015 (a fonte aceita
> qualquer `anoExercicio`), enquanto `GetGraficosEvolucaoAnualAplicacao`
> só devolve uma janela fixa de 5 anos terminando no ano pedido — por
> isso essa segunda consulta deixou de ser chamada, substituída pela
> série ano a ano (mais anos, e com todos os campos que a API devolve,
> não só o percentual: valor liquidado, **valor declarado** pelo
> município, valor por habitante e o **ranking oficial do TCE-ES**, tanto
> por valor total quanto por habitante). Extração testada de ponta a
> ponta no GitHub Actions: 632 chamadas (79 entidades × 8 anos), zero
> erros, menos de 2 minutos. `montar.py` grava essa série em
> `m[].historico` (por município) e `es.limiteConstitucional.historico`
> (ES), com degradação graciosa por ano/entidade faltante. O site
> (`site/tce/index.html`) ganhou a seção **"Série histórica (8 anos)"**,
> reativa ao filtro de município, com um gráfico (Chart.js, mesmo padrão
> visual das demais seções) alternável entre duas visões — valor aplicado
> combinado com percentual da receita (duas escalas: barras + linha, igual
> ao gráfico de Evolução) e valor por habitante — e uma tabela ano a ano
> com o ranking oficial do TCE-ES. Validado por simulação local via jsdom
> (sem erros JS, com e sem município selecionado, nas duas visões) antes
> de publicar. **Revisão de 19/10/2026:** o gráfico passou de três métricas
> alternáveis (valor, percentual, per capita) para duas, combinando valor e
> percentual no mesmo gráfico — ver changelog mais abaixo.
>
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
> **Gestão estadual** foi testada em duas fontes diferentes e não é
> possível em nenhuma delas: no Power BI, a tabela de fatos só registra
> lançamento por município, sem linha de gasto estadual direto (ver nota
> em `extrair.py`). Na API REST (16/10/2026), os ids de esfera
> administrativa 80 (Consórcio do Estado) e 81 (Estado do Espírito Santo)
> não retornam dado próprio nos endpoints de município, e o endpoint
> `EstadoControllers/Saude/GetSumario` devolve a mesma soma agregada dos
> 78 municípios que já temos (não o orçamento próprio do governo
> estadual em saúde). Conclusão: nenhuma das fontes atualmente usadas
> expõe o gasto estadual direto; seria preciso outra fonte (ex.: SIOPS,
> portal da transparência do Estado) para atender esse pedido.
> **Reconfirmado em 19/10/2026:** a descoberta do filtro por esfera
> administrativa (que abriu subfunção por município) reabriu essa
> pergunta — testamos `kpi_aplicacao_total`, `evolucao_por_ano`,
> `kpi_valor_medio_habitante` e `tabela_aplicacao_por_subfuncao` trocando
> o "Not In" que exclui `Estado do Espírito Santo` e `Consórcio do Estado
> do Espírito Santo` por um "In" explícito para cada uma, usando a mesma
> medida `Formulas._SomaLiquidado` já validada em produção. Resultado:
> as 4 consultas voltam vazias/nulas para as duas entidades (ver
> `resultados/teste-gestao-estadual.json`) — confirma que essas entidades
> existem na dimensão `DIM_EsferaAdministrativa`, mas não têm registro
> próprio na tabela de fatos usada neste relatório (plausível que sejam
> apenas categorias de classificação, sem execução orçamentária
> lançada diretamente nelas). Mantém-se a conclusão: não dá para extrair
> o gasto próprio do Governo do Estado a partir deste painel; seria
> preciso outra fonte.
>
> **Pedido do Rafael em 16/10/2026 (ajustes finos):** Presidente Kennedy
> (distorção por royalties de petróleo) excluído do destaque de
> maior/menor valor por habitante do panorama geral (ver `montar.py`).
> Competência em análise (período de referência) ganhou um selo
> destacado no topo da página, em vez do badge discreto anterior.
> Quadro de **valor liquidado em saúde** e **receita (calculada)** foi
> adicionado — como a API REST só expõe o percentual já calculado, a
> receita é obtida por cálculo direto (valor liquidado ÷ percentual),
> deixado explícito na página como derivação, não dado bruto da fonte.
> Gráfico de evolução ganhou rótulos com os valores sobre as barras/linha
> (plugin `chartjs-plugin-datalabels`). O quadro de "gasto por subfunção"
> só existia em nível estadual na consulta Power BI capturada (não por
> município); ao selecionar um município a página passou a deixar isso
> explícito em vez de simplesmente continuar mostrando o ES sem aviso —
> todas as demais seções (KPIs, limite constitucional, evolução, ranking,
> leitura estratégica) já atualizavam corretamente por município.
> **Correção de 19/10/2026:** essa limitação não era da fonte, e sim da
> consulta capturada — ver changelog mais abaixo (gasto por subfunção por
> município).
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
  → **todos os campos usados desde 19/10/2026**: `aplicacao` (valor
  liquidado), `valorDeclarado` (valor declarado pelo próprio ente — pode
  diferir do liquidado em anos encerrados, por retificação/auditoria;
  os dois são gravados, nenhum descartado), `aplicacaoPercentual`
  (percentual da receita aplicado — **o indicador oficial do limite de
  15%**), `aplicacaoPerCapita`, `participacaoMunicipal`/
  `participacaoPerCapitaMunicipal` (média de referência do ES naquele
  ano — mesmo valor em todos os municípios do mesmo ano, por isso
  tratada como dado do ES, não do município) e `rankingMunicipal`/
  `rankingPerCapitaMunicipal` (ranking oficial do TCE-ES, por valor
  total e por habitante). Aceita qualquer `anoExercicio` — testamos
  (`testar_historico.py`) e confirmamos dado real desde pelo menos 2015.
- `GET /api/EstadoControllers/Saude/GetSumario?anoExercicio=<ano>` →
  o mesmo indicador agregado para o Espírito Santo inteiro (sem
  `valorDeclarado`, `participacaoMunicipal` nem ranking — campos que só
  existem na resposta por município).
- `GET /api/MunicipioControllers/Saude/GetGraficosEvolucaoAnualAplicacao?idEsferaAdministrativa=<id>&anoExercicio=<ano>`
  → **não é mais chamada desde 19/10/2026**. Descoberta nos testes de
  profundidade histórica: devolve sempre uma janela fixa de 5 anos
  terminando no `anoExercicio` pedido (ex.: `anoExercicio=2019` traz
  2015-2019; `anoExercicio=2026` traz 2022-2026) — nunca acumula mais que
  isso, então não serve para uma série de 8 anos. Chamar `GetSumario` uma
  vez por ano cobre mais anos e traz mais campos (ver acima). Mantida
  apenas como referência histórica desta nota e em `testar_api_rest.py`.

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
  decodifica, **e também** chama `extrair_serie_historica_rest()`, que
  busca TODOS os campos do `GetSumario` da API REST própria (ver seção
  acima) para o ES e cada um dos 78 municípios, em cada um dos últimos 8
  anos a contar do ano mais recente (`JANELA_HISTORICO_ANOS`) — 632
  chamadas HTTP leves, com um pequeno pool de threads (6 workers) e novas
  tentativas com backoff em falha transitória. Grava tudo num único JSON
  com os dados brutos (ainda não é o formato final do site). Aceita um
  ano mais recente opcional (`python extrair.py saida.json 2025` — a
  janela de 8 anos passa a terminar nesse ano). **Desde 19/10/2026**,
  também chama `extrair_subfuncao_por_municipio()`: reenvia a mesma
  consulta Power BI de subfunção, acrescentando ao `Where` um filtro
  `IN DIM_EsferaAdministrativa.Nome = <município>` (fonte `"d1"` da
  consulta) — reproduz por HTTP puro o filtro "Esfera administrativa" do
  painel, que a consulta original capturada não usava. 78 chamadas em
  paralelo (4 workers), erros tolerados por município.
- `testar_api_rest.py`: teste de acesso isolado à API REST (usado para
  confirmar que respondia de IP de nuvem antes de integrar a produção).
- `testar_historico.py`: teste de profundidade histórica (19/10/2026) —
  confirmou que `GetSumario` tem dado real desde pelo menos 2015 e que
  `GetGraficosEvolucaoAnualAplicacao` só devolve uma janela fixa de 5
  anos (ver seção acima). Resultado em
  `resultados/teste-historico-tce-es.json`.
- `montar.py`: transforma a saída de `extrair.py` no `dados.json` final da
  página (`meta` com `anosHistorico`, `es` com os KPIs, a série `evolucao`
  por ano (Power BI, 2020 em diante) e `limiteConstitucional` (percentual,
  aplicação, per capita e população do ES mais recentes, **e** `historico`
  com a série de 8 anos — `[ano, aplicacao, percentual, perCapita,
  participacaoMediaMunicipal, participacaoPerCapitaMediaMunicipal]`),
  `subfuncoes` com valor e variação, `m` com os 78 municípios — valor por
  habitante, variação, população, cobertura de plano de saúde privado,
  `limitePercentual`/`limiteValorLiquidado`/`limiteValorDeclarado`/
  `limiteRanking`/`limiteRankingPerCapita` do ano mais recente, **e**
  `historico` com a série de 8 anos por município — `[ano, aplicacao,
  valorDeclarado, percentual, perCapita, rankingAplicacao,
  rankingPerCapita]` —, **e** `subfuncoes` (desde 19/10/2026) com o gasto
  por subfunção do próprio município (mesmo formato de `subfuncoes` do
  ES, `[nome, valor]`), ou `null` quando o município não teve esse dado
  nessa extração. Degradação graciosa: ano ou entidade sem dado na série
  histórica, ou município sem dado de subfunção, fica de fora (não trava
  o pipeline); se a API REST falhar por completo numa execução, os campos
  de limite/histórico ficam `null` e o resto publica normalmente. Valida
  (`validar()`) antes de gravar: aplicação e valor por habitante
  positivos, percentual com plano entre 0 e 1, pelo menos 70 municípios,
  série histórica com pelo menos 6 dos 8 anos e presente em pelo menos 60
  dos 78 municípios, e subfunção por município presente em pelo menos 60
  dos 78.
  **Exclusão do destaque de maior/menor valor por habitante:** a pedido
  do Rafael em 16/10/2026, `EXCLUIR_DOS_EXTREMOS_PANORAMA` em `montar.py`
  tira Presidente Kennedy do cálculo dos KPIs "Maior/menor valor por
  habitante" do panorama geral dos 78 municípios — o valor per capita do
  município é inflado por royalties de petróleo, não por gestão de
  saúde, e distorcia a comparação. O município continua normalmente na
  tabela, no ranking e em todos os demais cálculos (só sai desse
  destaque específico). Para excluir outro município do mesmo destaque
  no futuro, adicionar o nome ao mesmo conjunto.
- `enviar.py`: publica `dados.json` em `partelli.pro/tce` por FTP(S), nos
  mesmos moldes do `robo/enviar.py` (guarda a versão anterior como
  `dados_anterior.json`). **Também reenvia `site/tce/index.html` e
  `.htaccess` a cada execução** (lidos direto do repositório, relativo ao
  próprio script) — por isso uma mudança só na página (sem mexer em
  `extrair.py`/`montar.py`) só vai ao ar depois de uma execução do
  workflow `robo_tce_es.yml` (manual via `workflow_dispatch` ou no
  próximo agendamento); só dar `git push` não publica a página sozinho.
  Credenciais em `~/.config/robo_tce_es/.env` (modelo em `.env.exemplo`).
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

Nessa mesma seção, um quadro dedicado mostra **valor liquidado em saúde**
e **receita (calculada)** — somente em cards (ES ou município
selecionado); a receita é calculada a partir do valor liquidado e do
percentual declarado, com nota explicando que não é um valor bruto da
fonte (não entra como coluna na tabela dos 78 municípios, para não
sobrecarregar a tabela — ver ajuste de 16/10/2026 abaixo). A competência
em análise (período de referência, ex. "jan a set/2026") aparece em
destaque logo abaixo do título da página, com aviso quando o ano ainda
está parcial. O gráfico de evolução por ano mostra os valores (R$
milhões e variação %) diretamente sobre as barras/linha, não só no
tooltip. O "Menor valor por habitante" do panorama geral exclui
Presidente Kennedy (ver nota acima); os cards "Municípios com dado
disponível" e "Maior valor por habitante" foram removidos do panorama
geral a pedido do Rafael em 16/10/2026.

> **Ajuste de 16/10/2026 (revisão de usabilidade):** a seção "Gasto por
> subfunção" deixou de misturar o dado estadual com o contexto do
> município selecionado — agora mostra um aviso separado e explícito
> ("não há quebra por município disponível") em vez de exibir o número
> global sem indicação. A tabela dos 78 municípios voltou a ter 8
> colunas (as duas de receita/liquidado saíram, ficando só nos cards) e
> ganhou um layout responsivo: em telas estreitas (≤760px), cada linha
> vira um cartão empilhado com rótulo ao lado do valor, para nunca
> precisar de rolagem horizontal. O dropdown de filtro por município
> passou a listar os 78 em ordem alfabética (o array de dados em si
> continua ordenado por valor por habitante, usado como ordenação padrão
> da tabela; só a lista do `<select>` segue o nome).

> **Atualização de 19/10/2026 (série histórica de 8 anos):** nova seção
> **"Série histórica (8 anos)"**, reativa ao filtro de município (ou ao
> panorama do ES), com três métricas alternáveis por botão — valor
> aplicado, percentual da receita (limite de 15%, com linha tracejada de
> referência) e valor por habitante — num gráfico de linha (mesmo padrão
> visual e biblioteca das demais seções). Abaixo, uma tabela ano a ano com
> valor liquidado, valor declarado (quando município selecionado — os dois
> podem diferir em anos encerrados, por retificação/auditoria; nenhum é
> descartado), percentual da receita, valor por habitante e o **ranking
> oficial do TCE-ES** (por valor total e por habitante). Ao selecionar um
> município, um texto também mostra sua posição no ranking oficial do ano
> mais recente. Validado por simulação local via jsdom (sem erros JS) e
> por execução real do pipeline completo no GitHub Actions antes de
> publicar.
>
> **Revisão de 19/10/2026 (pedido do Rafael — verificação pós-publicação):**
> quatro pontos conferidos/ajustados a partir do painel já publicado.
> 1) **Evolução da aplicação em saúde:** suspeita de erro de cálculo a
> partir de 2024 investigada ao vivo, comparando número a número com o
> painel oficial do TCE-ES (inclusive um teste cruzado acidental para
> Presidente Kennedy, que também bateu). Conclusão: não há erro de
> cálculo — os valores batem exatamente com a fonte; o salto visual em
> 2024 é dado real (aumento de execução declarada ao TCE-ES), não bug do
> robô. 2) **Série histórica:** o seletor de três métricas (valor,
> percentual, per capita) virou dois — valor e percentual combinados num
> único gráfico de duas escalas (barras + linha), igual ao padrão do
> gráfico de Evolução, e valor por habitante como segunda opção. 3)
> **Gasto por subfunção por município:** descoberta de que o filtro
> "Esfera administrativa" do painel (que a consulta Power BI capturada
> não usava) também funciona via HTTP puro — basta acrescentar uma
> condição `IN DIM_EsferaAdministrativa.Nome = <município>` ao `Where` da
> consulta de subfunção já existente. Validado ao vivo no navegador e via
> teste em GitHub Actions (`resultados/teste-subfuncao-municipio.json`,
> 3 municípios, totais batendo com `m[].aplicado` já publicado). Isso
> **corrige a limitação documentada nos itens acima** ("só nível
> estadual") — não era da fonte, era da consulta capturada sem o filtro.
> Implementado em `extrair.py` (`extrair_subfuncao_por_municipio()`, 78
> chamadas em paralelo, erros tolerados por município),  `montar.py`
> (`m[].subfuncoes`, com degradação graciosa — se um município não tiver
> esse dado na extração, a página volta a mostrar o panorama do ES com
> aviso, em vez de quebrar) e `site/tce/index.html`
> (`renderSubfuncao()`). 4) **Agendamento e textos:** cron confirmado em
> `30 9 * * 1,3,5` (09:30 UTC = 06:30 Brasília, seg/qua/sex — sem
> alteração) e os textos deste README/LEIA-ME e do site revisados para
> não deixar nenhuma referência às "três métricas" antigas ou à
> limitação de subfunção que não é mais verdadeira.

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
