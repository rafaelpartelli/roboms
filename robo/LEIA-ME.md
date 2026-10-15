# Robô do Radar de Recursos SUS ES (partelli.pro/fundo)

Atualiza diariamente, às 10h15, o arquivo `fundo/dados.json` do site com os dados dos Painéis InvestSUS do Fundo Nacional de Saúde.

## O que ele faz

1. **extrair.py**: abre o InvestSUS em um navegador automático e executa as consultas do `extrair.js` (repasses fundo a fundo, saldos por tipo de conta, repasses por conta e emendas). Leva cerca de 15 segundos.
2. **montar.py**: transforma os dados brutos no `dados.json` do site e confere o resultado (78 municípios, totais acima de zero).
3. **robo.sh**: executa tudo. Se a extração falhar, tenta mais duas vezes com intervalo de 5 minutos. Se o saldo total variar mais de 40% em relação à última publicação, **não publica** e registra o motivo no log.
4. **enviar.py**: envia o arquivo por FTP e guarda a versão anterior como `dados_anterior.json`.

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

## Acompanhamento

- Logs diários: `~/robo_investsus/logs/AAAA-MM-DD.log`
- Rodar manualmente: `~/robo_investsus/robo.sh`
- Ver agendamento: `crontab -l`
- A página mostra no selo "Atualizado em" a data e hora da última extração.

## Limitações conhecidas

- Se o FNS mudar a estrutura dos painéis (identificadores dos aplicativos ou nomes de campos), a extração falha e o site mantém os últimos dados publicados.
- O painel oficial não traz saldos de 2020 a 2025; a série histórica tem essa lacuna.
