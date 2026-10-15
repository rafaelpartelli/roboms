#!/usr/bin/env python3
"""Abre os Painéis InvestSUS em um navegador automático e extrai os dados brutos do ES.

Uso: python3 extrair.py saida.json
"""
import json, os, sys, pathlib
from playwright.sync_api import sync_playwright

URL = 'https://investsuspaineis.saude.gov.br/extensions/CGIN_InvestsusPaineis/CGIN_InvestsusPaineis.html'
JS = (pathlib.Path(__file__).parent / 'extrair.js').read_text(encoding='utf-8')
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')


def main(saida):
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=os.environ.get('HEADLESS', '1') != '0')
        pag = nav.new_page(user_agent=UA, locale='pt-BR', viewport={'width': 1366, 'height': 900})
        pag.goto(URL, wait_until='domcontentloaded', timeout=120_000)
        pag.wait_for_function("typeof require === 'function'", timeout=120_000)
        pag.wait_for_timeout(5000)
        pag.add_script_tag(content=JS)
        bruto = pag.evaluate("() => extrairInvestsus('ES')")
        nav.close()
    pathlib.Path(saida).write_text(json.dumps(bruto, ensure_ascii=False), encoding='utf-8')
    print('extração ok:', {k: (len(v) if isinstance(v, list) else v) for k, v in bruto.items() if k != 'apps'})


if __name__ == '__main__':
    main(sys.argv[1])
