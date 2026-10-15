#!/bin/bash
# Publica saida/radar.json no site (FTP da Hostinger, exigindo TLS).
# Nenhuma senha fica neste arquivo. Defina no .env (com "export"):
#   export FTP_HOST=185.239.210.135
#   export FTP_USER=u339642306.partelli.pro      # ideal: conta FTP dedicada so para a pasta radar
#   export FTP_PASS='sua-senha-ftp'
#   export FTP_DIR=public_html/radar             # opcional (este e o padrao)
#   export FTP_CERT_HOST=nome.do.certificado     # so se o certificado nao valer para o numero do servidor
#   export RADAR_PUBLISH_CMD="bash $HOME/robo_dou/publicar_radar.sh"
# Teste manual:
#   cd ~/robo_dou && set -a && source ./.env && set +a && bash publicar_radar.sh
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ARQ="$DIR/saida/radar.json"

for v in FTP_HOST FTP_USER FTP_PASS; do
  if [ -z "${!v:-}" ]; then echo "publicar_radar: defina $v no .env"; exit 1; fi
done
[ -f "$ARQ" ] || { echo "publicar_radar: $ARQ nao existe"; exit 1; }

# Valida antes de subir: JSON legivel e com pelo menos uma portaria
python3 - "$ARQ" <<'PY' || { echo "publicar_radar: radar.json invalido ou vazio, nada publicado"; exit 1; }
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert isinstance(d.get("portarias"), list) and len(d["portarias"]) > 0
PY

# Usuario e senha vao por stdin (nao aparecem na lista de processos)
cred() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
# Se o certificado do servidor vale para um nome (e nao para o numero), usa o nome e aponta para o IP
ALVO="${FTP_CERT_HOST:-$FTP_HOST}"
RES=(); [ -n "${FTP_CERT_HOST:-}" ] && RES=(--resolve "${FTP_CERT_HOST}:21:${FTP_HOST}")
printf 'user = "%s:%s"\n' "$(cred "$FTP_USER")" "$(cred "$FTP_PASS")" |
  curl -sS --fail --ssl-reqd --ftp-create-dirs ${RES[@]+"${RES[@]}"} -K - \
       -T "$ARQ" "ftp://${ALVO}/${FTP_DIR:-public_html/radar}/radar.json" \
  && echo "radar.json publicado em $(date -Is)"
