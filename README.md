# roboms

Robô do **Radar de Recursos SUS: Espírito Santo** (https://partelli.pro/gestor/recursos/).

Lê diariamente os Painéis InvestSUS do Fundo Nacional de Saúde (repasses fundo a fundo, saldos em conta e emendas parlamentares), monta o arquivo `dados.json` e publica no site por FTP.

## Estrutura

- `robo/extrair.js` e `robo/extrair.py`: abrem o InvestSUS em navegador automático e extraem os dados brutos do ES.
- `robo/montar.py`: transforma os dados brutos no `dados.json` da página e confere os totais.
- `robo/enviar.py`: envia ao site e guarda a versão anterior como `dados_anterior.json`.
- `.github/workflows/robo.yml`: execução manual em Actions › Run workflow. O agendamento diário está desligado porque o InvestSUS bloqueia os servidores do GitHub (teste de 15/10/2026, HTTP 403); a rotina diária roda no computador do Rafael.
- `.github/workflows/teste.yml`: teste rápido de acesso ao InvestSUS.

## Segredos necessários (Settings › Secrets and variables › Actions)

| Nome | Valor |
|---|---|
| `FTP_HOST` | 185.239.210.135 |
| `FTP_USUARIO` | u339642306.partelli.pro |
| `FTP_SENHA` | senha da conta FTP |

A senha fica só nos segredos do GitHub e nunca aparece no código nem nos registros.

## Trava de segurança

Se o saldo total variar mais de 40% em relação ao que está publicado, o robô não publica e a execução aparece com erro em Actions.
