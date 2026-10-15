#!/usr/bin/env bash
# Robô diário do Radar de Recursos SUS ES (partelli.pro/fundo)
# extrai do InvestSUS -> monta dados.json -> confere -> envia ao site
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
HOJE=$(date +%Y-%m-%d)
mkdir -p bruto saida logs
# roda uma vez por dia: se já publicou hoje, encerra (o agendamento confere a cada 10 minutos e ao ligar o computador)
if [ "${1:-}" != "--forcar" ] && [ -f saida/ultimo_ok ] && [ "$(cat saida/ultimo_ok)" = "$HOJE" ]; then exit 0; fi
# evita duas execuções ao mesmo tempo
exec 9>"$DIR/.robo.lock"; flock -n 9 || exit 0
LOG="logs/$HOJE.log"
exec >>"$LOG" 2>&1
echo "=== $(date '+%d/%m/%Y %H:%M:%S') início ==="
# espera a internet ficar disponível (até 15 minutos), útil logo depois de ligar o computador
for i in $(seq 1 30); do
  curl -s -o /dev/null -m 15 https://investsuspaineis.saude.gov.br/ && break
  [ "$i" -eq 1 ] && echo "aguardando conexão com a internet..."
  sleep 30
done

PY="$DIR/.venv/bin/python"
for tentativa in 1 2 3; do
  if [ $tentativa -eq 1 ]; then CMD=("$PY" extrair.py "bruto/$HOJE.json");
  else CMD=(xvfb-run -a env HEADLESS=0 "$PY" extrair.py "bruto/$HOJE.json"); fi
  if "${CMD[@]}"; then break; fi
  echo "falha na extração (tentativa $tentativa)"; [ $tentativa -eq 3 ] && exit 1; sleep 120
done

"$PY" montar.py "bruto/$HOJE.json" "saida/dados.json"

# trava de segurança: não publica se o saldo total variar mais de 40% em relação à última publicação
if [ -f saida/publicado.json ]; then
  "$PY" - <<'EOF'
import json,sys
n=json.load(open('saida/dados.json')); a=json.load(open('saida/publicado.json'))
tot=lambda d: sum(m['s'] for m in d['m'])+d['EST']['s']
tn,ta=tot(n),tot(a)
fb=lambda d: sum(m['fb'] for m in d['m'])+d['EST']['fb']
if n['meta']['anoFaf']==a['meta']['anoFaf'] and fb(a) and not 0.6<fb(n)/fb(a)<1.5:
    sys.exit(f"variação suspeita do fundo a fundo: {fb(a):.0f} -> {fb(n):.0f}; publicação suspensa")
if ta and abs(tn/ta-1)>0.4:
    sys.exit(f'variação suspeita do saldo total: {ta:.0f} -> {tn:.0f}; publicação suspensa')
print(f'saldo total: {ta:.0f} -> {tn:.0f}')
EOF
fi

"$PY" enviar.py saida/dados.json
cp saida/dados.json saida/publicado.json
echo "$HOJE" > saida/ultimo_ok
# mantém 60 dias de histórico bruto e logs
find bruto -name '*.json' -mtime +60 -delete; find logs -name '*.log' -mtime +60 -delete
echo "=== $(date '+%d/%m/%Y %H:%M:%S') concluído ==="
