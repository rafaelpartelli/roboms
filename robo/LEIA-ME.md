# Robô do Radar de Recursos SUS: Brasil, 26 estados e DF (partelli.pro/fundo)

**Agenda: semanal, toda sexta-feira a partir das 15h** (decisão de 23/10/2026; antes era diária). O cron confere a cada 10 minutos e ao ligar o computador; a rodada roda na primeira verificação a partir de sexta 15h e, se o computador estiver desligado nesse horário, assim que ele for ligado. A página considera o dado "defasado" após 8 dias e mostra a data da próxima atualização.

Atualiza semanalmente os arquivos de dados do site com os Painéis InvestSUS do Fundo Nacional de Saúde, um por UF, e o resumo nacional usado no mapa do Brasil:

| Arquivo no site | Conteúdo | Página |
|---|---|---|
| `fundo/brasil.json` | totais por UF (repasse, emendas, saldo, população, data de extração) | partelli.pro/gestor/recursos/ (mapa e ranking dos estados) |
| `fundo/dados.json` | Espírito Santo, por município | partelli.pro/gestor/recursos/?uf=es |
| `fundo/dados-xx.json` | demais UFs (`xx` = sigla minúscula), por município | partelli.pro/gestor/recursos/?uf=xx |

Histórico: ES desde 13/10/2026; MG e MA incluídos em 22/10/2026; todas as UFs e o mapa do Brasil em 23/10/2026. O DF é tratado como ente único (Fundo de Saúde do DF, sem municípios). Para mudar a lista de UFs, ajuste `UFS` em `robo.sh` (ou rode `UFS="ES MG" ./robo.sh --forcar`) e a quantidade esperada em `montar.py` (`ESPERADOS`).

A página mostra sempre, em destaque no topo, a data da extração, a idade do dado (com aviso de "dado defasado" acima de 8 dias) e a data da próxima atualização; no mapa, cada estado tem a sua data no ranking e na caixa de detalhe.

## O que ele faz

1. **extrair.py**: abre o InvestSUS em um navegador automático e executa as consultas do `extrair.js` (repasses fundo a fundo, saldos por tipo de conta, repasses por conta e emendas) para cada UF, gravando `bruto/AAAA-MM-DD-UF.json`. O `robo.sh` chama o `extrair.py` uma vez por UF (processo e navegador novos a cada estado), o que libera memória e escreve o progresso no log em tempo real. Primeira rodada completa (23/10/2026, notebook de 4 GB): 27 UFs publicadas em 1 hora (17:50 a 18:49); UFs pequenas levam de 15 a 60 segundos, MG e SP vários minutos. Nessa rodada, ainda com um processo único, o sistema encerrou a extração por falta de memória no último estado (TO), recuperado na segunda tentativa; por isso a mudança para um processo por UF. Falha em uma UF não impede as outras.
2. **montar.py**: transforma os dados brutos no JSON do site, restaura os acentos dos nomes de municípios (lista oficial do IBGE em `municipios_ibge.json`) e confere o resultado (quantidade de municípios da UF, totais acima de zero). Com `--anterior`, compara com a última publicação daquela UF.
3. **robo.sh**: executa tudo, UF por UF. Se a extração falhar, tenta mais duas vezes com intervalo de 2 minutos; depois disso, o agendamento tenta de novo no máximo 4 rodadas por dia. Se o saldo total de uma UF variar mais de 40% (ou o fundo a fundo sair da faixa de 60% a 150%) em relação à última publicação, **aquela UF não é publicada** e o motivo vai para o log.
4. **enviar.py**: envia cada arquivo por FTP com o mesmo nome e guarda a versão anterior como `dados_anterior.json`, `dados-mg_anterior.json` etc.
5. **Resumo nacional**: ao fim de cada rodada com publicação, `montar.py --resumo` junta a última versão publicada de cada UF em `brasil.json` e envia ao site.

## Instalação (uma única vez, no servidor)

1. Copie esta pasta para `~/robo_investsus`.
2. No hPanel da Hostinger, em **Arquivos > Contas FTP**, anote servidor, usuário e senha (ou crie uma conta FTP restrita à pasta `public_html/fundo` do partelli.pro).
3. No terminal:

```bash
cd ~/robo_investsus
bash instalar.sh
```

O instalador cria o ambiente Python, instala o navegador automático, pede as credenciais FTP (gravadas só no servidor, em `~/.config/robo_investsus/.env`, com acesso restrito ao seu usuário), testa a conexão, agenda a execução semanal (sextas, 15h) e já roda a primeira atualização.

Se você criar uma conta FTP restrita à pasta `fundo`, informe `.` quando o instalador pedir a pasta do site.

## Atualizar o robô já instalado

No computador onde ele roda:

```bash
bash ~/robo_investsus/atualizar.sh
```

O script baixa a versão do GitHub e mantém o agendamento; só roda a extração se a rodada da semana estiver pendente. Para forçar uma rodada completa agora (cerca de 1 hora): `bash ~/robo_investsus/atualizar.sh --forcar`.

## Acompanhamento

- Logs (um arquivo por dia de execução): `~/robo_investsus/logs/AAAA-MM-DD.log`
- Rodar manualmente: `~/robo_investsus/robo.sh --forcar` (todas as UFs) ou `UFS=MG ~/robo_investsus/robo.sh --forcar` (só uma)
- Marcas de publicação do dia: `saida/ultimo_ok_<UF>` (uma por UF)
- Ver agendamento: `crontab -l`
- A página mostra no selo "Atualizado em" a data e hora da última extração.

## Limitações conhecidas

- Se o FNS mudar a estrutura dos painéis (identificadores dos aplicativos ou nomes de campos), a extração falha e o site mantém os últimos dados publicados.
- O painel oficial não traz saldos de 2020 a 2025; a série histórica tem essa lacuna.
