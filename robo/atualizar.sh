#!/usr/bin/env bash
# Atualiza o robô a partir do GitHub, ativa a atualização automática ao ligar e roda agora.
set -euo pipefail
DIR="$HOME/robo_investsus"; cd "$DIR"
BASE=https://raw.githubusercontent.com/rafaelpartelli/roboms/main/robo
for f in extrair.js extrair.py montar.py enviar.py municipios_ibge.json robo.sh atualizar.sh; do curl -fsSL "$BASE/$f?$(date +%s)" -o "$f.novo" && mv "$f.novo" "$f"; done
chmod +x robo.sh atualizar.sh
# agendamento: ao ligar (após 2 min) e a cada 10 minutos; o robô publica só uma vez por dia
( crontab -l 2>/dev/null | grep -v 'robo_investsus/robo.sh' ; \
  echo "@reboot sleep 120 && $DIR/robo.sh"; \
  echo "*/10 * * * * $DIR/robo.sh" ) | crontab -
systemctl is-active --quiet cron || sudo systemctl enable --now cron
echo "Agendamento ativo:"; crontab -l | grep robo_investsus
echo "Rodando a atualização agora..."
"$DIR/robo.sh" --forcar || true
tail -n 6 "$DIR/logs/$(date +%F).log"
