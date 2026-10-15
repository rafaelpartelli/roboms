# Robô DOU: Radar Diário de Portarias do Ministério da Saúde

Baixa diariamente o Diário Oficial da União pelo INLABS (Imprensa Nacional), filtra as **portarias do Ministério da Saúde** (Seção 1 e edições extras), gera um CSV em `saida/` e atualiza `saida/radar.json`, lido pela página Radar Saúde do site partelli.pro.

## Arquivos

| Arquivo | Função |
|---|---|
| `robo_dou.py` | Robô principal (login no INLABS, filtro, CSV, e-mail opcional, radar.json) |
| `run_robo.sh` | Executa o robô com o ambiente virtual e as credenciais do `.env` |
| `publicar_radar.sh` | Envia o `radar.json` ao site por FTP com TLS |
| `robo-dou.service` / `robo-dou.timer` | Agendamento systemd (todos os dias às 09:30) |
| `requirements.txt` | Dependências Python |
| `.env.exemplo` | Modelo das variáveis; copiar para `.env` e preencher |

## Instalação no computador

```bash
cd ~/robo_dou
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.exemplo .env && nano .env
mkdir -p ~/.config/systemd/user && cp robo-dou.service robo-dou.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now robo-dou.timer
```

## Integração

Às 09:45 dos dias úteis, uma tarefa agendada do Claude no computador lê o CSV do dia e envia o relatório executivo para rafael@partelli.pro.

## Segurança

Senhas ficam apenas no `.env` local (ignorado pelo Git). Nenhuma credencial está no código.
