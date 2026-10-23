#!/usr/bin/env python3
"""Envia o JSON de uma UF (dados.json do ES, dados-mg.json etc.) ou o resumo brasil.json para partelli.pro/fundo por FTP seguro (FTPS).
O arquivo é publicado com o mesmo nome que tem no computador; a versão anterior fica como <nome>_anterior.json.

Credenciais lidas de ~/.config/robo_investsus/.env (criado pelo instalar.sh):
  FTP_HOST, FTP_USUARIO, FTP_SENHA, FTP_PASTA (ex.: domains/partelli.pro/public_html/fundo)
Uso: python3 enviar.py saida/dados.json  (ou saida/dados-mg.json etc.)
"""
import ftplib, os, re, sys, pathlib

ENV = pathlib.Path.home() / '.config' / 'robo_investsus' / '.env'


def ler_env():
    cfg = {}
    for linha in ENV.read_text(encoding='utf-8').splitlines():
        if '=' in linha and not linha.strip().startswith('#'):
            k, v = linha.split('=', 1); cfg[k.strip()] = v.strip()
    # aceita o servidor digitado como ftp://1.2.3.4/ ou ftp.site.com:21
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
    pastas = [cfg.get('FTP_PASTA', ''), 'domains/partelli.pro/public_html/fundo', 'public_html/fundo', 'fundo']
    for p in [x for x in pastas if x]:
        try:
            ftp.cwd('/'); ftp.cwd(p); return ftp
        except ftplib.error_perm:
            continue
    raise SystemExit('pasta fundo do site não encontrada no FTP; confira FTP_PASTA em ' + str(ENV))


def enviar(arquivo):
    nome = pathlib.Path(arquivo).name
    base = nome[:-5] if nome.endswith('.json') else nome
    if not re.fullmatch(r'dados(-[a-z]{2})?|brasil', base):
        raise SystemExit('nome de arquivo inesperado: ' + nome)
    cfg = ler_env(); ftp = conectar(cfg)
    nomes = ftp.nlst()
    if nome in nomes:  # guarda a versão anterior
        try: ftp.delete(f'{base}_anterior.json')
        except ftplib.error_perm: pass
        ftp.rename(nome, f'{base}_anterior.json')
    with open(arquivo, 'rb') as f:
        ftp.storbinary(f'STOR {base}_novo.json', f)
    ftp.rename(f'{base}_novo.json', nome)
    tam = ftp.size(nome); ftp.quit()
    print('envio ok:', nome, tam, 'bytes')


if __name__ == '__main__':
    if sys.argv[1] == '--testar':
        f = conectar(ler_env()); print('conexão ok, pasta:', f.pwd(), 'arquivos:', f.nlst()); f.quit()
    else:
        enviar(sys.argv[1])
