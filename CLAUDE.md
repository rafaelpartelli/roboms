# Orientação para criar robôs neste repositório

Este repositório (`roboms`) é a casa de **todos os robôs** de Rafael Partelli daqui para frente: coleta de dados públicos de saúde (DOU, InvestSUS, futuros robôs de CNES, SIGTAP, editais etc.) e publicação no site partelli.pro. Este arquivo reúne o que os robôs existentes (InvestSUS e DOU) já ensinaram, para que cada robô novo siga o mesmo padrão sem repetir os mesmos erros.

## 1. Antes de escrever a primeira linha

Pergunte e registre a resposta no `LEIA-ME.md` do robô:

1. **Onde a fonte permite acesso?** GitHub Actions roda em IPs dos EUA e várias fontes bloqueiam isso:
   - InvestSUS (FNS): bloqueia servidores do GitHub (HTTP 403, testado 15/10/2026).
   - INLABS (Imprensa Nacional): exige login e também falha em IP de nuvem compartilhada.
   - Teste manual primeiro (`workflow_dispatch` no Actions, ou `curl`/navegador automático de um servidor de nuvem) antes de programar o agendamento automático. Só desligue o agendamento em Actions se o teste confirmar bloqueio; não assuma.
2. **Onde ele vai rodar de fato?** Em ordem de preferência, quando a fonte permite:
   - **GitHub Actions** (agendado): sem custo de manutenção, logs e histórico no próprio GitHub. Preferir sempre que a fonte não bloquear.
   - **Hostinger (cron da hospedagem)**: quando a fonte não bloqueia o IP da hospedagem. Mesmo ambiente do site, então a publicação é local (sem FTP).
   - **Computador do Rafael (systemd/cron)**: último recurso, só quando a fonte exige algo que só o computador tem (ex.: navegador com sessão específica) ou quando nenhum dos anteriores funciona. Tem o maior custo: depende do computador estar ligado, ninguém monitora falhas automaticamente.
   - **Tarefa agendada do Claude**: para robôs que são essencialmente pesquisa e redação (ex.: a newsletter Radar Saúde Pública), não extração estruturada de uma fonte específica.
3. **Quem publica o resultado?** Decida a pasta de destino no site (`partelli.pro/<área>/`) e documente no README principal.

## 2. Estrutura de pastas

Cada robô vive em sua própria pasta na raiz do repositório (como `robo/` e `robo_dou/`), com:

```
nome-do-robo/
  LEIA-ME.md          # o que faz, como instalar, onde roda, dependências
  .env.exemplo         # modelo das variáveis de ambiente, SEM valores reais
  extrair.*            # coleta os dados brutos da fonte
  montar.*             # transforma dados brutos no JSON/CSV final e confere totais
  enviar.*             # publica o resultado (FTP, cópia local, e-mail)
  robo.sh / run_*.sh    # script único que encadeia extrair → montar → enviar, usado pelo agendador
  requirements.txt      # dependências Python, se houver
```

Separar extração, montagem e envio em arquivos diferentes facilita testar cada etapa isolada e reaproveitar código entre robôs.

## 3. Segurança: credenciais

- **Nenhuma senha, token ou chave entra no código, no README ou em qualquer arquivo versionado.** Tudo vem de variáveis de ambiente lidas de um `.env` local, nunca versionado.
- Todo robô tem um `.env.exemplo` versionado, com os nomes das variáveis e um valor fictício, para quem for instalar.
- Quando o robô roda em **GitHub Actions**, as credenciais vão em Settings → Secrets and variables → Actions, nunca em texto no workflow.
- Quando o robô roda no **Hostinger**, o `.env` fica fora do `public_html` (ou em pasta protegida) e nunca é lido pelo navegador.
- Em scripts shell que mandam usuário/senha para `curl`/`ftp`, sempre pelo stdin (`-K -`) e nunca como argumento de linha de comando, que aparece na lista de processos do sistema.
- Antes de qualquer commit ou push, rode uma verificação simples por palavras como `senha`, `password`, `secret`, `token`, `key` fora dos arquivos `.exemplo`, e confira o resultado manualmente.

## 4. Travas de segurança no dado

Todo robô que publica números (saldos, totais, contagens) deve comparar o resultado novo com o último publicado e **recusar publicar** se a variação for absurda (foi usado o limite de 40% no InvestSUS). Isso evita que uma falha de extração publique zero, dado truncado ou duplicado no site. Registre o motivo da recusa no log/execução para dar para investigar depois.

## 5. Documentação

- **`LEIA-ME.md` de cada robô**: o que faz, estrutura dos arquivos, como instalar, variáveis de ambiente necessárias, onde roda e agenda.
- **`README.md` da raiz do repositório**: tabela única com todos os robôs (nome, pasta, onde roda, agenda, saída), atualizada a cada robô novo ou mudança de onde ele roda.
- Ao desativar, migrar ou substituir um robô, atualizar o README e o LEIA-ME no mesmo commit, não deixar desatualizado "para depois".

## 6. `.gitignore`

Nunca versionar: `.env`, ambientes virtuais (`venv/`, `.venv/`), `__pycache__/`, logs, dados brutos de extração, saídas geradas localmente, arquivos de lock (`.robo.lock`) e backups (`*.bak*`). O `.gitignore` da raiz já cobre os padrões comuns; adicione os específicos de cada robô novo lá mesmo.

## 7. Antes de colocar em produção (agendar de verdade)

1. Rodar manualmente pelo menos uma vez do jeito que vai rodar em produção (mesmo ambiente/credenciais).
2. Confirmar que o resultado publicado no site está correto (abrir a página, não só o JSON).
3. Checar o log dessa execução por erros silenciosos (uma execução pode "terminar sem erro" e mesmo assim ter falhado em login, por exemplo, e publicado dado velho; isso já aconteceu).
4. Só então ativar o agendamento (timer/cron/Actions).
5. Avisar o Rafael onde o robô ficou agendado e com que frequência, para constar no histórico de decisões.

## 8. Ao desativar um robô

1. Desativar o agendamento (não só pausar a tarefa que consome o resultado, se houver uma separada).
2. Verificar se alguma outra rotina depende do resultado desse robô (ex.: um relatório ou newsletter que lê o arquivo gerado por ele) e avisar ou ajustar.
3. Atualizar README e LEIA-ME no mesmo commit, registrando a data e o motivo.
4. Manter o código no repositório (não apagar a pasta) a menos que o Rafael peça para remover.
