#!/usr/bin/env bash
# Instalação do robô do Radar de Recursos SUS (ES, MG e MA) no servidor Ubuntu.
# Rode uma vez, dentro da pasta do robô:  bash instalar.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "1/5 Criando ambiente Python..."
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q playwright

echo "2/5 Instalando o navegador automático (pode pedir sua senha de administrador)..."
.venv/bin/python -m playwright install chromium
sudo apt-get install -y -qq xvfb >/dev/null 2>&1 || true
sudo .venv/bin/python -m playwright install-deps chromium || echo "Aviso: dependências do sistema não instaladas; se a extração falhar, rode: sudo $DIR/.venv/bin/python -m playwright install-deps chromium"

echo "3/5 Credenciais de FTP da Hostinger (hPanel > Arquivos > Contas FTP)"
CFG="$HOME/.config/robo_investsus"; mkdir -p "$CFG"; chmod 700 "$CFG"
read -rp "  Servidor FTP [185.239.210.135]: " H
H=${H#*://}; H=${H%%/*}; H=${H%%:*}; H=${H:-185.239.210.135}
read -rp "  Usuário FTP [u339642306.partelli.pro]: " U
U=${U:-u339642306.partelli.pro}
S=""; while [ -z "$S" ]; do read -rsp "  Senha FTP (não aparece ao digitar): " S; echo; done
read -rp "  Pasta do site [domains/partelli.pro/public_html/fundo]: " P
P=${P:-domains/partelli.pro/public_html/fundo}
umask 077
printf 'FTP_HOST=%s\nFTP_USUARIO=%s\nFTP_SENHA=%s\nFTP_PASTA=%s\n' "$H" "$U" "$S" "$P" > "$CFG/.env"
chmod 600 "$CFG/.env"

echo "4/5 Testando conexão com o site..."
.venv/bin/python enviar.py --testar

echo "5/5 Agendando: uma atualização por dia, na primeira hora em que o computador estiver ligado entre 8h15 e 22h15..."
chmod +x robo.sh
( crontab -l 2>/dev/null | grep -v 'robo_investsus/robo.sh' ; echo "@reboot sleep 120 && $DIR/robo.sh"; echo "*/10 * * * * $DIR/robo.sh" ) | crontab -

echo "Rodando a primeira execução agora (cerca de 1 minuto)..."
"$DIR/robo.sh" --forcar && tail -n 5 "$DIR/logs/$(date +%Y-%m-%d).log"
echo "Pronto. O robô atualiza o site uma vez por dia, sempre que o computador estiver ligado. Logs em $DIR/logs/"
