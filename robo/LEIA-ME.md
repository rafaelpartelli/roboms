# Robô do Radar de Recursos SUS: ES, MG e MA (partelli.pro/fundo)

Atualiza diariamente os arquivos de dados do site com os Painéis InvestSUS do Fundo Nacional de Saúde, um por estado:

| UF | Arquivo no site | Página | Municípios esperados |
|---|---|---|---|
| ES | `fundo/dados.json` | partelli.pro/gestor/recursos/ | 78 |
| MG | `fundo/dados-mg.json` | partelli.pro/gestor/recursos/?uf=mg | 853 |
| MA | `fundo/dados-ma.json` | partelli.pro/gestor/recursos/?uf=ma | 217 |

Minas Gerais e Maranhão foram incluídos em 22/10/2026. Para mudar a lista de estados, ajuste `UFS` em `robo.sh` (ou rode `UFS="ES MG" ./robo.sh`), a quantidade esperada em `montar.py` (`ESPERADOS`), os nomes oficiais em `municipios_ibge.json` e o bloco `UFS` no início do script da página `site/gestor/recursos/index.html`.

## O que ele faz

1. **extrair.py**: abre o InvestSUS em um navegador automático e executa as consultas do `extrair.js` (repasses fundo a fundo, saldos por tipo de conta, repasses por conta e emendas) para cada UF, gravando `bruto/AAAA-MM-DD-UF.json`. O ES leva cerca de 15 segundos; MG, por ter 853 municípios, pode levar vários minutos. Falha em uma UF não impede as outras.
2. **montar.py**: transforma os dados brutos no JSON do site, restaura os acentos dos nomes de municípios (lista oficial do IBGE em `municipios_ibge.json`) e confere o resultado (quantidade de municípios da UF, totais acima de zero). Com `--anterior`, compara com a última publicação daquela UF.
3. **robo.sh**: executa tudo, UF por UF. Se a extração falhar, tenta mais duas vezes com intervalo de 2 minutos; depois disso, o agendamento tenta de novo no máximo 4 rodadas por dia. Se o saldo total de uma UF variar mais de 40% (ou o fundo a fundo sair da faixa de 60% a 150%) em relação à última publicação, **aquela UF não é publicada** e o motivo vai para o log.
4. **enviar.py**: envia cada arquivo por FTP com o mesmo nome e guarda a versão anterior como `dados_anterior.json`, `dados-mg_anterior.json` etc.

## Instalação (uma única vez, no servidor)

1. Copie esta pasta para `~/robo_investsus`.
2. No hPanel da Hostinger, em **Arquivos > Contas FTP**, anote servidor, usuário e senha (ou crie uma conta FTP restrita à pasta `public_html/fundo` do partelli.pro).
3. No terminal:

```bash
cd ~/robo_investsus
bash instalar.sh
```

O instalador cria o ambiente Python, instala o navegador automático, pede as credenciais FTP (gravadas só no servidor, em `~/.config/robo_investsus/.env`, com acesso restrito ao seu usuário), testa a conexão, agenda a execução diária e já roda a primeira atualização.

Se você criar uma conta FTP restrita à pasta `fundo`, informe `.` quando o instalador pedir a pasta do site.

## Atualizar o robô já instalado

No computador onde ele roda:

```bash
bash ~/robo_investsus/atualizar.sh
```

O script baixa a versão do GitHub, mantém o agendamento e roda uma atualização completa na hora (com MG, conte alguns minutos).

## Acompanhamento

- Logs diários: `~/robo_investsus/logs/AAAA-MM-DD.log`
- Rodar manualmente: `~/robo_investsus/robo.sh --forcar` (todas as UFs) ou `UFS=MG ~/robo_investsus/robo.sh --forcar` (só uma)
- Marcas de publicação do dia: `saida/ultimo_ok_ES`, `saida/ultimo_ok_MG`, `saida/ultimo_ok_MA`
- Ver agendamento: `crontab -l`
- A página mostra no selo "Atualizado em" a data e hora da última extração.

## Limitações conhecidas

- Se o FNS mudar a estrutura dos painéis (identificadores dos aplicativos ou nomes de campos), a extração falha e o site mantém os últimos dados publicados.
- O painel oficial não traz saldos de 2020 a 2025; a série histórica tem essa lacuna.
