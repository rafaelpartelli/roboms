#!/bin/bash
# Executa o robô com o ambiente virtual e as credenciais do .env
cd "$HOME/robo_dou" || exit 1
source venv/bin/activate
source ./.env
python3 robo_dou.py --email >> log.txt 2>&1
# Publica o radar.json no site, se RADAR_PUBLISH_CMD estiver definido no .env (ex.: comando sftp/rsync). Sem ele, so gera o arquivo.
[ -n "$RADAR_PUBLISH_CMD" ] && bash -c "$RADAR_PUBLISH_CMD" >> log.txt 2>&1
