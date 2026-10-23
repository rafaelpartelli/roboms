#!/usr/bin/env python3
"""Abre os Painéis InvestSUS em um navegador automático e extrai os dados brutos por UF.

Uso:
  python3 extrair.py bruto/2026-10-23 ES MG MA   -> grava bruto/2026-10-23-ES.json, -MG.json, -MA.json (qualquer UF)
  python3 extrair.py saida.json                  -> só ES, no arquivo indicado (forma antiga)

Cada UF é extraída de forma independente: se uma falhar, as demais são gravadas.
Código de saída 0 se todas deram certo, 1 se alguma falhou.
"""
import json, os, sys, time, pathlib
from playwright.sync_api import sync_playwright

URL = 'https://investsuspaineis.saude.gov.br/extensions/CGIN_InvestsusPaineis/CGIN_InvestsusPaineis.html'
JS = (pathlib.Path(__file__).parent / 'extrair.js').read_text(encoding='utf-8')
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')


def abrir(pw):
    nav = pw.chromium.launch(headless=os.environ.get('HEADLESS', '1') != '0')
    pag = nav.new_page(user_agent=UA, locale='pt-BR', viewport={'width': 1366, 'height': 900})
    pag.set_default_timeout(30 * 60_000)  # estados grandes (MG) levam vários minutos
    pag.goto(URL, wait_until='domcontentloaded', timeout=120_000)
    pag.wait_for_function("typeof require === 'function'", timeout=120_000)
    pag.wait_for_timeout(5000)
    pag.add_script_tag(content=JS)
    return nav, pag


def main(destino, ufs):
    falhas = []
    with sync_playwright() as pw:
        for uf in ufs:
            saida = destino if destino.endswith('.json') else f'{destino}-{uf}.json'
            t0 = time.time(); nav = None
            try:
                # navegador novo a cada UF: libera memória (MG e SP são grandes) e isola falhas
                nav, pag = abrir(pw)
                bruto = pag.evaluate("uf => extrairInvestsus(uf)", uf)
            except Exception as erro:
                print(f'{uf}: falha na extração: {str(erro)[:300]}')
                falhas.append(uf)
                continue
            finally:
                if nav:
                    try: nav.close()
                    except Exception: pass
            pathlib.Path(saida).write_text(json.dumps(bruto, ensure_ascii=False), encoding='utf-8')
            resumo = {k: (len(v) if isinstance(v, list) else v) for k, v in bruto.items() if k not in ('apps', 'uf')}
            print(f'{uf}: extração ok em {time.time() - t0:.0f}s', resumo)
    if falhas: print('UFs com falha:', ' '.join(falhas))
    return 1 if falhas else 0


if __name__ == '__main__':
    destino = sys.argv[1]
    ufs = [u.upper() for u in sys.argv[2:]] or ['ES']
    sys.exit(main(destino, ufs))
