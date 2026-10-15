#!/usr/bin/env bash
# Robô do Painel TCE-ES: Gastos com a Função Saúde (partelli.pro/tce)
# extrai do Painel de Controle do TCE-ES -> monta dados.json -> confere -> envia ao site
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
HOJE=$(date +%Y-%m-%d)
mkdir -p bruto saida logs
LOG="logs/$HOJE.log"
exec >>"$LOG" 2>&1
echo "=== $(date '+%d/%m/%Y %H:%M:%S') início ==="

PY="python3"
command -v "$DIR/.venv/bin/python" >/dev/null 2>&1 && PY="$DIR/.venv/bin/python"

"$PY" extrair.py "bruto/$HOJE.json"
"$PY" montar.py "bruto/$HOJE.json" "saida/dados.json"

# trava de segurança: não publica se a aplicação total ou o valor por habitante
# variarem mais de 40% em relação à última publicação (mesmo padrão do robô InvestSUS)
if [ -f saida/publicado.json ]; then
  "$PY" - <<'EOF'
import json, sys
n = json.load(open('saida/dados.json')); a = json.load(open('saida/publicado.json'))
for chave, rotulo in [('aplicacao', 'aplicação total'), ('valorHab', 'valor médio por habitante')]:
    vn, va = n['es'].get(chave), a['es'].get(chave)
    if va and not 0.6 < (vn / va) < 1.5:
        sys.exit(f"variação suspeita em {rotulo}: {va:.0f} -> {vn:.0f}; publicação suspensa")
print('aplicação:', a['es']['aplicacao'], '->', n['es']['aplicacao'])
EOF
fi

"$PY" enviar.py saida/dados.json
cp saida/dados.json saida/publicado.json
find bruto -name '*.json' -mtime +90 -delete; find logs -name '*.log' -mtime +90 -delete
echo "=== $(date '+%d/%m/%Y %H:%M:%S') concluído ==="
