#!/usr/bin/env python3
"""
Teste temporario (de servidor de nuvem, sem navegador) para descobrir ate
onde a API REST do Painel de Controle do TCE-ES tem dado historico, antes
de decidir ate que ano voltar na serie de 8 anos pedida pelo Rafael em
19/10/2026.

Testa GetSumario e GetGraficosEvolucaoAnualAplicacao para uma faixa de anos
(incluindo anos bem antigos, para achar o limite real da fonte) e para dois
municipios diferentes, e tambem confirma se GetGraficosEvolucaoAnualAplicacao
muda o range retornado conforme o parametro anoExercicio varia (ou se
sempre devolve a mesma janela fixa).

Uso: python testar_historico.py saida.json
"""
import json
import sys

import requests

BASE = "https://paineldecontrole.tcees.tc.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{BASE}/municipio/2026/afonso-claudio/gestaoFiscal/saude",
}

ANOS_TESTE = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2026]
# Afonso Claudio (id 1) e Vitoria (id 77), usados nos testes anteriores
MUNICIPIOS_TESTE = {"afonso_claudio": 1, "vitoria": 77}


def chamar(caminho: str, params: dict) -> dict:
    resp = requests.get(f"{BASE}{caminho}", headers=HEADERS, params=params, timeout=20)
    return {"status_http": resp.status_code, "corpo": _tentar_json(resp)}


def _tentar_json(resp):
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return resp.text[:300]


def main(out_path: str) -> int:
    resultado = {"sumario_por_ano": {}, "evolucao_por_ano_parametro": {}, "erros": {}}

    for apelido, id_esfera in MUNICIPIOS_TESTE.items():
        resultado["sumario_por_ano"][apelido] = {}
        for ano in ANOS_TESTE:
            chave = str(ano)
            try:
                resultado["sumario_por_ano"][apelido][chave] = chamar(
                    "/api/MunicipioControllers/Saude/GetSumario",
                    {"anoExercicio": ano, "idEsferaAdministrativa": id_esfera},
                )
            except Exception as e:  # noqa: BLE001
                resultado["erros"][f"sumario_{apelido}_{chave}"] = str(e)[:300]

        # Verifica se o parametro anoExercicio muda a janela da evolucao anual
        # (ex.: anoExercicio=2019 traz 2015-2019? ou sempre a mesma janela
        # fixa recente, independente do ano pedido?)
        resultado["evolucao_por_ano_parametro"][apelido] = {}
        for ano in [2019, 2022, 2026]:
            chave = str(ano)
            try:
                resultado["evolucao_por_ano_parametro"][apelido][chave] = chamar(
                    "/api/MunicipioControllers/Saude/GetGraficosEvolucaoAnualAplicacao",
                    {"idEsferaAdministrativa": id_esfera, "anoExercicio": ano},
                )
            except Exception as e:  # noqa: BLE001
                resultado["erros"][f"evolucao_{apelido}_{chave}"] = str(e)[:300]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Teste de profundidade historica: API REST TCE-ES ===")
    for apelido in MUNICIPIOS_TESTE:
        for ano in ANOS_TESTE:
            r = resultado["sumario_por_ano"][apelido].get(str(ano))
            if r:
                print(f"  sumario {apelido} {ano}: HTTP {r['status_http']} -> {json.dumps(r['corpo'])[:150]}")
    return 1 if resultado["erros"] else 0


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "teste_historico.json"
    sys.exit(main(saida))
