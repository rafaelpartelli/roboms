#!/usr/bin/env python3
"""Envia o dados.json (e, se presentes, a página estática index.html e o
.htaccess de ../site/tce/) para partelli.pro/tce por FTP seguro (FTPS).

Credenciais lidas de ~/.config/robo_tce_es/.env (criado pelo instalar.sh):
  FTP_HOST, FTP_USUARIO, FTP_SENHA, FTP_PASTA (ex.: domains/partelli.pro/public_html/tce)
Uso: python3 enviar.py dados.json
"""
import ftplib, os, re, sys, pathlib

PAGINA_DIR = pathlib.Path(__file__).parent.parent / 'site' / 'tce'

ENV = pathlib.Path.home() / '.config' / 'robo_tce_es' / '.env'


def ler_env():
    cfg = {}
    for linha in ENV.read_text(encoding='utf-8').splitlines():
        if '=' in linha and not linha.strip().startswith('#'):
            k, v = linha.split('=', 1); cfg[k.strip()] = v.strip()
    h = re.sub(r'^[a-zA-Z]+://', '', cfg.get('FTP_HOST', '').strip()).strip('/')
    cfg['FTP_HOST'] = h.split('/')[0].split(':')[0]
    return cfg


def conectar(cfg):
    if not cfg.get('FTP_HOST'):
        raise SystemExit('servidor FTP não informado em ' + str(ENV))
    try:
        ftp = ftplib.FTP_TLS(cfg['FTP_HOST'], timeout=60)
        ftp.login(cfg['FTP_USUARIO'], cfg['FTP_SENHA'])
        ftp.prot_p()
    except Exception as erro:
        print('aviso: FTP seguro indisponível, usando FTP padrão:', erro)
        ftp = ftplib.FTP(cfg['FTP_HOST'], timeout=60)
        ftp.login(cfg['FTP_USUARIO'], cfg['FTP_SENHA'])
    pastas = [cfg.get('FTP_PASTA', ''), 'domains/partelli.pro/public_html/tce', 'public_html/tce', 'tce']
    for p in [x for x in pastas if x]:
        try:
            ftp.cwd('/'); ftp.cwd(p); return ftp
        except ftplib.error_perm:
            continue
    raise SystemExit('pasta tce do site não encontrada no FTP; confira FTP_PASTA em ' + str(ENV))


def enviar(arquivo):
    cfg = ler_env(); ftp = conectar(cfg)
    nomes = ftp.nlst()
    if 'dados.json' in nomes:  # guarda a versão anterior
        try: ftp.delete('dados_anterior.json')
        except ftplib.error_perm: pass
        ftp.rename('dados.json', 'dados_anterior.json')
    with open(arquivo, 'rb') as f:
        ftp.storbinary('STOR dados_novo.json', f)
    ftp.rename('dados_novo.json', 'dados.json')
    tam = ftp.size('dados.json')
    # página estática: reenviada sempre (arquivo pequeno), para publicar qualquer
    # atualização de layout feita no repositório junto com o próximo dado
    for nome in ('index.html', '.htaccess'):
        caminho = PAGINA_DIR / nome
        if caminho.exists():
            with open(caminho, 'rb') as f:
                ftp.storbinary(f'STOR {nome}', f)
    ftp.quit()
    print('envio ok: dados.json', tam, 'bytes; página estática reenviada')


if __name__ == '__main__':
    if sys.argv[1] == '--testar':
        f = conectar(ler_env()); print('conexão ok, pasta:', f.pwd(), 'arquivos:', f.nlst()); f.quit()
    else:
        enviar(sys.argv[1])
