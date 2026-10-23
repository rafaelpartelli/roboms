#!/usr/bin/env bash
# Robô diário do Radar de Recursos SUS (partelli.pro/fundo): 26 estados e Distrito Federal
# extrai do InvestSUS -> monta o JSON de cada UF -> confere -> envia ao site -> atualiza o resumo do mapa (brasil.json)
# Cada UF é publicada de forma independente: falha em uma não impede as outras.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
HOJE=$(date +%Y-%m-%d)
UFS="${UFS:-ES AC AL AP AM BA CE DF GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO}"
FORCAR=0; [ "${1:-}" = "--forcar" ] && FORCAR=1
mkdir -p bruto saida logs

arquivo() { [ "$1" = ES ] && echo dados.json || echo "dados-$(echo "$1" | tr 'A-Z' 'a-z').json"; }
publicado() { [ "$1" = ES ] && echo saida/publicado.json || echo "saida/publicado-$1.json"; }

# migração: marca antiga de execução do ES
[ -f saida/ultimo_ok ] && [ ! -f saida/ultimo_ok_ES ] && cp saida/ultimo_ok saida/ultimo_ok_ES

# UFs que ainda não foram publicadas hoje (o agendamento confere a cada 10 minutos e ao ligar o computador)
PEND=()
for uf in $UFS; do
  if [ $FORCAR -eq 1 ] || [ "$(cat "saida/ultimo_ok_$uf" 2>/dev/null)" != "$HOJE" ]; then PEND+=("$uf"); fi
done
[ ${#PEND[@]} -eq 0 ] && exit 0

# evita duas execuções ao mesmo tempo
exec 9>"$DIR/.robo.lock"; flock -n 9 || exit 0
# no máximo 4 rodadas por dia com falha, para não ocupar o computador o dia inteiro
TENT="saida/rodadas_$HOJE"
if [ $FORCAR -eq 0 ]; then
  N=$(cat "$TENT" 2>/dev/null || echo 0); [ "$N" -ge 4 ] && exit 0; echo $((N + 1)) > "$TENT"
fi
find saida -name 'rodadas_*' ! -name "rodadas_$HOJE" -delete 2>/dev/null || true

LOG="logs/$HOJE.log"
exec >>"$LOG" 2>&1
echo "=== $(date '+%d/%m/%Y %H:%M:%S') início: ${PEND[*]} ==="
# lista oficial de nomes de municípios (acentos); baixa se ainda não existir
[ -s municipios_ibge.json ] || curl -fsSL "https://raw.githubusercontent.com/rafaelpartelli/roboms/main/robo/municipios_ibge.json" -o municipios_ibge.json || echo "aviso: sem lista de nomes do IBGE"
# espera a internet ficar disponível (até 15 minutos), útil logo depois de ligar o computador
for i in $(seq 1 30); do
  curl -s -o /dev/null -m 15 https://investsuspaineis.saude.gov.br/ && break
  [ "$i" -eq 1 ] && echo "aguardando conexão com a internet..."
  sleep 30
done

PY="$DIR/.venv/bin/python"
for uf in "${PEND[@]}"; do rm -f "bruto/$HOJE-$uf.json"; done
for tentativa in 1 2 3; do
  FALTA=()
  for uf in "${PEND[@]}"; do [ -s "bruto/$HOJE-$uf.json" ] || FALTA+=("$uf"); done
  [ ${#FALTA[@]} -eq 0 ] && break
  [ $tentativa -gt 1 ] && { echo "falha na extração de ${FALTA[*]} (tentativa $((tentativa - 1)))"; sleep 120; }
  # um processo por UF: libera a memória a cada estado (no notebook de 4 GB o processo único foi encerrado por falta de memória em 23/10/2026)
  for uf in "${FALTA[@]}"; do
    if [ $tentativa -eq 1 ]; then "$PY" -u extrair.py "bruto/$HOJE" "$uf" || true
    else xvfb-run -a env HEADLESS=0 "$PY" -u extrair.py "bruto/$HOJE" "$uf" || true; fi
  done
done

ERROS=0; NOVAS=0
for uf in "${PEND[@]}"; do
  B="bruto/$HOJE-$uf.json"; A="saida/$(arquivo "$uf")"; P="$(publicado "$uf")"
  if [ ! -s "$B" ]; then echo "$uf: extração falhou nas 3 tentativas"; ERROS=1; continue; fi
  # monta, valida e compara com a última publicação (trava de 40% no saldo)
  if ! "$PY" montar.py "$B" "$A" --anterior "$P"; then echo "$uf: publicação suspensa"; ERROS=1; continue; fi
  if ! "$PY" enviar.py "$A"; then echo "$uf: falha no envio"; ERROS=1; continue; fi
  cp "$A" "$P"
  echo "$HOJE" > "saida/ultimo_ok_$uf"
  [ "$uf" = ES ] && echo "$HOJE" > saida/ultimo_ok
  echo "$uf: publicado"; NOVAS=1
done

# resumo nacional para o mapa do Brasil, com a última versão publicada de cada UF
if [ $NOVAS -eq 1 ] || [ $FORCAR -eq 1 ]; then
  if "$PY" montar.py --resumo saida/brasil.json saida/publicado*.json && "$PY" enviar.py saida/brasil.json; then echo "resumo nacional publicado"
  else echo "falha no resumo nacional"; ERROS=1; fi
fi

# mantém 60 dias de histórico bruto e logs
find bruto -name '*.json' -mtime +60 -delete; find logs -name '*.log' -mtime +60 -delete
echo "=== $(date '+%d/%m/%Y %H:%M:%S') concluído ==="
exit $ERROS
