# roboms

Robôs de Rafael Partelli para acesso a dados do Ministério da Saúde e monitoramento da gestão do SUS.

| Robô | Pasta | Onde roda | Agenda | Saída |
|---|---|---|---|---|
| Radar de Recursos SUS: Espírito Santo (InvestSUS/FNS) | `robo/` | Computador do Rafael (cron); GitHub Actions só manual | Diária | https://partelli.pro/gestor/recursos/ |
| Radar Diário de Portarias MS (DOU/INLABS) | `robo_dou/` | **Hostinger** (cron, dias úteis 8h30 e 11h00). Versão local desativada em 15/10/2026 | Dias úteis | https://partelli.pro/radar/ |
| Radar Saúde Pública (newsletter) | `tarefas_agendadas/` | Tarefa agendada do Claude (nuvem) | Seg, qua e sex às 06:53 | Newsletter HTML por e-mail |
| Painel TCE-ES: Gastos com a função saúde | `robo_tce_es/` | **GitHub Actions** (HTTP puro, sem navegador) — falta cadastrar os segredos de FTP neste repositório | Seg, qua e sex às 06:30 | https://partelli.pro/tce |

## 1. Radar de Recursos SUS: Espírito Santo (`robo/`)

Lê diariamente os Painéis InvestSUS do Fundo Nacional de Saúde (repasses fundo a fundo, saldos em conta e emendas parlamentares), monta o arquivo `dados.json` e publica no site por FTP.

- `robo/extrair.js` e `robo/extrair.py`: abrem o InvestSUS em navegador automático e extraem os dados brutos do ES.
- `robo/montar.py`: transforma os dados brutos no `dados.json` da página e confere os totais.
- `robo/enviar.py`: envia ao site e guarda a versão anterior como `dados_anterior.json`.
- `.github/workflows/robo.yml`: execução manual em Actions › Run workflow. O agendamento diário está desligado porque o InvestSUS bloqueia os servidores do GitHub (teste de 15/10/2026, HTTP 403); a rotina diária roda no computador do Rafael.
- `.github/workflows/teste.yml`: teste rápido de acesso ao InvestSUS.

### Segredos necessários (Settings › Secrets and variables › Actions)

| Nome | Valor |
|---|---|
| `FTP_HOST` | 185.239.210.135 |
| `FTP_USUARIO` | u339642306.partelli.pro |
| `FTP_SENHA` | senha da conta FTP |

A senha fica só nos segredos do GitHub e nunca aparece no código nem nos registros.

### Trava de segurança

Se o saldo total variar mais de 40% em relação ao que está publicado, o robô não publica e a execução aparece com erro em Actions.

## 2. Radar Diário de Portarias MS (`robo_dou/`)

Baixa o Diário Oficial da União pelo INLABS, filtra as portarias do Ministério da Saúde, grava CSV e `radar.json` e, opcionalmente, envia e-mail e publica no site. **Produção:** roda no Hostinger (`~/robo_dou/run_hostinger.sh`), com arquivo mensal em `radar/arquivo/`. **A cópia desta pasta é a versão local antiga**, desativada em 15/10/2026 (login no INLABS falhando desde 09/10); falta trazer para cá a versão do Hostinger. Detalhes e instalação em `robo_dou/LEIA-ME.md`. Credenciais apenas no `.env` local (modelo em `robo_dou/.env.exemplo`).

## 3. Radar Saúde Pública (`tarefas_agendadas/`)

Cópia de referência da instrução da tarefa agendada do Claude que produz a newsletter. Serve para versionar e recriar a tarefa se necessário.

## 4. Painel TCE-ES: Gastos com a função saúde (`robo_tce_es/`)

Acompanha os gastos com a função saúde por município do Painel de Controle do TCE-ES (https://paineldecontrole.tcees.tc.br), incorporado como relatório Power BI "publicar na web" (sem API REST própria do TCE-ES). A chamada de dados interna do Power BI é sem estado e pode ser reenviada via HTTP puro (`extrair.py`), sem navegador — confirmado contra os números reais da tela (R$ 3,65 Bi aplicado, R$ 880,38/habitante, 17,63% com plano privado, ranking por município e por subfunção). Pipeline completo (`extrair.py` → `montar.py` → `enviar.py`) e testado de ponta a ponta no GitHub Actions, agendado para segundas, quartas e sextas às 06:30 Brasília, publicando em **partelli.pro/tce**. A página reaproveita os mesmos componentes visuais (KPIs, alertas, gráficos, ranking ordenável, leitura estratégica) do Radar de Recursos SUS (`/gestor/recursos/`), com filtro por município. **Pendência:** faltam cadastrar os segredos `FTP_HOST`/`FTP_USUARIO`/`FTP_SENHA` *neste repositório* (mesmos valores do robô `robo/`) — sem eles o passo de envio falha e o `dados.json` publicado hoje continua sendo o que foi colocado manualmente (schema antigo). Detalhes completos em `robo_tce_es/LEIA-ME.md`.

## Segurança

Nenhuma senha, `.env`, ambiente virtual, log ou dado bruto é versionado (ver `.gitignore`).
