# Robô TCE-ES: Painel de Controle (recorte saúde)

> **Situação em 15/10/2026:** fase de teste de acesso. Ainda não extrai nem publica dados — só valida se dá para alcançar a fonte e capturar a chamada de dados de dentro do GitHub Actions.

## O que é

Painel de Controle do Tribunal de Contas do Espírito Santo (https://paineldecontrole.tcees.tc.br), recorte da área temática **Saúde**. O site do TCE-ES tem 6 painéis de saúde, todos como páginas do **mesmo relatório Power BI "publicar na web"**:

| Página (pageName) | O que mostra |
|---|---|
| (a identificar) | Estabelecimentos de saúde (CNES) |
| (a identificar) | Distribuição de leitos |
| (a identificar) | Distribuição de equipamentos |
| `ReportSection544931c3083d7668ba47` | **Gastos com a função saúde** — aplicação por município, valor médio por habitante, gastos por subfunção, variação ano a ano, população com plano de saúde privado (ANS) |
| (a identificar) | Planos Municipais de Saúde |
| (a identificar) | Detalhamento dos planos de saúde |

Prioridade: **Gastos com a função saúde**, por ser o recorte financeiro (complementa o [[robo]] InvestSUS/FNS, que olha repasses do governo federal; este painel olha o valor efetivamente aplicado por cada município, por fonte diferente — contas públicas fiscalizadas pelo TCE-ES).

Chave do relatório (mesma para todas as páginas, só troca o `pageName`):
- `k` (chave pública): `0b4992ae-e680-4f0c-b307-83c889f69479`
- `t` (tenant): `9d1437b1-472c-4501-9439-dcfe9a41f2b0`

## Por que isso muda o jeito de extrair

O Painel de Controle **não tem API REST própria aberta**. Cada painel temático é incorporado via iframe `app.powerbi.com/view?r=<token>&pageName=<página>`. Os números que aparecem na tela (ex.: "R$ 3,65 Bi em aplicação em saúde") vêm de uma chamada interna do próprio Power BI para a infraestrutura da Microsoft (`*.analysis.windows.net` ou similar), não de um endpoint do tcees.tc.br.

Isso muda a pergunta "onde a fonte permite acesso?" do item 1 do `CLAUDE.md` raiz: aqui o risco de bloqueio não é do governo brasileiro (como FNS e INLABS), e sim se a Microsoft bloqueia ou limita esse tipo de automação. **Ainda não testado.**

## Teste de acesso (passo atual)

`testar_acesso.py`: abre o relatório com Playwright, intercepta as respostas de rede que parecem ser a chamada de dados do Power BI, e grava um resumo em JSON (`resultado_teste.json`) com veredito `ACESSO_OK_COM_DADOS` ou `SEM_CHAMADA_DE_DADOS_CAPTURADA`.

Rodar manualmente: GitHub → Actions → **"Teste de acesso ao Painel TCE-ES (Power BI)"** → Run workflow. O resultado é gravado em `resultados/teste-acesso-tce-es.json` no repositório e também fica como artefato de execução (com captura de tela).

**Não testado ainda a partir de um ambiente de nuvem com saída de rede irrestrita** (o teste local feito num sandbox restrito falhou por causa de um proxy que bloqueia `app.powerbi.com`, não por bloqueio da fonte — por isso o teste real precisa rodar no Actions).

## Próximos passos (depois que o teste confirmar acesso)

1. Analisar a chamada de dados capturada (formato "DSR" do Power BI) e escrever `extrair.py` que faz esse mesmo request programaticamente (sem precisar renderizar a página inteira toda vez), ou mantém Playwright se o formato for complexo demais para replay direto.
2. Escrever `montar.py` que transforma a resposta em algo equivalente ao `dados.json` do robô InvestSUS: valores por município, ano de referência, variação em relação ao ano anterior.
3. Definir onde publicar no site (`partelli.pro/<área>/`, a combinar com o Rafael) e escrever `enviar.py`.
4. Aplicar a trava de variação (seguir o padrão de 40% usado no InvestSUS) antes de qualquer publicação automática.
5. Decidir onde roda em produção (GitHub Actions, Hostinger ou computador), seguindo a ordem de preferência do `CLAUDE.md` raiz, conforme o resultado do teste de acesso.
6. Se útil, repetir o processo para as outras 5 páginas do mesmo relatório (mesmo `k`/`t`, só muda `pageName` — falta identificar cada uma).

## Segurança

Nenhuma credencial é necessária nesta fase (o relatório é público, embutido com chave pública de leitura). Se isso mudar (ex.: a extração definitiva precisar de algum token de sessão), seguir o padrão do `CLAUDE.md` raiz: nada em código, tudo em `.env` local ou em Secrets do GitHub Actions.
