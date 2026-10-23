# roboms

Robôs de Rafael Partelli para acesso a dados do Ministério da Saúde e monitoramento da gestão do SUS.

| Robô | Pasta | Onde roda | Agenda | Saída |
|---|---|---|---|---|
| Radar de Recursos SUS: Brasil, 26 estados e DF (InvestSUS/FNS) | `robo/` | Computador do Rafael (cron); GitHub Actions só manual | Semanal: sextas a partir das 15h (desde 23/10/2026) | https://partelli.pro/gestor/recursos/ (mapa do Brasil; cada UF em `?uf=xx`) |
| Radar Diário de Portarias MS (DOU/INLABS) | `robo_dou/` | **Hostinger** (cron, dias úteis 8h30 e 11h00). Versão local desativada em 15/10/2026 | Dias úteis | https://partelli.pro/radar/ |
| Radar Saúde Pública (newsletter) | `tarefas_agendadas/` | Tarefa agendada do Claude (nuvem) | Seg, qua e sex às 06:53 | Newsletter HTML por e-mail |
| Painel TCE-ES: Gastos com a função saúde | `robo_tce_es/` | **GitHub Actions** (HTTP puro, sem navegador) | Seg, qua e sex às 06:30 | https://partelli.pro/tce |

## 1. Radar de Recursos SUS: Brasil, 26 estados e DF (`robo/`)

Lê semanalmente (toda sexta-feira a partir das 15h) os Painéis InvestSUS do Fundo Nacional de Saúde (repasses fundo a fundo, saldos em conta e emendas parlamentares) para as 27 UFs (todas desde 23/10/2026), monta um arquivo por UF (`dados.json` do ES, `dados-xx.json` das demais) e o resumo nacional `brasil.json`, e publica no site por FTP. A página abre no mapa interativo do Brasil, com ranking dos estados por escala de cor (6 indicadores), e cada estado abre o detalhe por município. A data de atualização fica sempre em destaque. Mapa: SVG Maps (@svg-maps/brazil), licença CC BY 4.0, em `site/gestor/recursos/mapa-brasil.json`.

- `robo/extrair.js` e `robo/extrair.py`: abrem o InvestSUS em navegador automático e extraem os dados brutos de cada UF.
- `robo/montar.py`: transforma os dados brutos no JSON da página, restaura acentos dos nomes (`robo/municipios_ibge.json`) e confere os totais.
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

Se o saldo total de um estado variar mais de 40% em relação ao que está publicado, o robô não publica aquele estado e registra o motivo (no log local ou como erro em Actions).

## 2. Radar Diário de Portarias MS (`robo_dou/`)

Baixa o Diário Oficial da União pelo INLABS, filtra as portarias do Ministério da Saúde, grava CSV e `radar.json` e, opcionalmente, envia e-mail e publica no site. **Produção:** roda no Hostinger (`~/robo_dou/run_hostinger.sh`), com arquivo mensal em `radar/arquivo/`. **A cópia desta pasta é a versão local antiga**, desativada em 15/10/2026 (login no INLABS falhando desde 09/10); falta trazer para cá a versão do Hostinger. Detalhes e instalação em `robo_dou/LEIA-ME.md`. Credenciais apenas no `.env` local (modelo em `robo_dou/.env.exemplo`).

## 3. Radar Saúde Pública (`tarefas_agendadas/`)

Cópia de referência da instrução da tarefa agendada do Claude que produz a newsletter. Serve para versionar e recriar a tarefa se necessário.

## 4. Painel TCE-ES: Gastos com a função saúde (`robo_tce_es/`)

Acompanha os gastos com a função saúde por município do Painel de Controle do TCE-ES (https://paineldecontrole.tcees.tc.br). Combina duas fontes: o relatório Power BI "publicar na web" do painel original (chamada de dados interna sem estado, reenviada via HTTP puro em `extrair.py`, sem navegador — confirmado contra os números reais da tela: R$ 3,65 Bi aplicado, R$ 880,38/habitante, 17,63% com plano privado, ranking por município e por subfunção) e a API REST própria de uma página irmã do mesmo painel (`/municipio/<ano>/<município>/gestaoFiscal/saude`), usada como modelo a pedido do Rafael. Essa API fornece o indicador oficial do limite constitucional de aplicação em saúde (mínimo de 15% da receita, EC 29/2000 e LC 141/2012), valor declarado, valor por habitante e o ranking oficial do TCE-ES, para o ES e para cada um dos 78 municípios — dado que o relatório Power BI não trazia. Desde 19/10/2026, a extração traz **todos os campos dessa API e uma série histórica de 8 anos** (GetSumario ano a ano, não só o ano mais recente), publicada como seção própria e dinâmica no site (gráfico combinando valor aplicado e percentual da receita, com opção de ver valor por habitante + tabela ano a ano com ranking oficial). O **gasto por subfunção** também passou a ter quebra por município (filtro por esfera administrativa reproduzido via HTTP puro na mesma consulta Power BI), além do panorama estadual. Pipeline completo (`extrair.py` → `montar.py` → `enviar.py`), testado de ponta a ponta e publicando de verdade no GitHub Actions, agendado para segundas, quartas e sextas às 06:30 Brasília, publicando em **partelli.pro/tce**. A página reaproveita os mesmos componentes visuais (KPIs, alertas, gráficos, ranking ordenável, leitura estratégica) do Radar de Recursos SUS (`/gestor/recursos/`), com filtro por município, e inclui seções dedicadas ao limite constitucional (velocímetro + comparação entre os 78 municípios), à série histórica de 8 anos e ao gasto por subfunção (estadual ou por município). Detalhes completos em `robo_tce_es/LEIA-ME.md`.

### Segredos necessários (Settings › Secrets and variables › Actions)

| Nome | Valor |
|---|---|
| `FTP_HOST` | 185.239.210.135 (mesmo valor do robô `robo/`) |
| `FTP_USUARIO` | u339642306.partelli.pro (mesmo valor do robô `robo/`) |
| `FTP_SENHA` | senha da conta FTP (mesmo valor do robô `robo/`) |

Cadastrados em 15/10/2026.

## Segurança

Nenhuma senha, `.env`, ambiente virtual, log ou dado bruto é versionado (ver `.gitignore`).
