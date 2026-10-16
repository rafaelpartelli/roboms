#!/usr/bin/env python3
"""
Teste de acesso (de servidor de nuvem, sem navegador) à API REST propria do
Painel de Controle do TCE-ES (paineldecontrole.tcees.tc.br) - um sistema
DIFERENTE do relatorio Power BI ja usado por extrair.py.

Objetivo: confirmar que essa API responde normalmente a partir de um IP de
nuvem compartilhada (GitHub Actions, IP dos EUA), antes de decidir usa-la em
producao - mesma cautela do CLAUDE.md usada para o InvestSUS/FNS (que
bloqueia) e o Power BI (que nao bloqueia).

Uso: python testar_api_rest.py saida.json
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


def main(out_path: str) -> int:
    resultado = {"testes": {}, "erros": {}}

    testes = {
        "settings": f"{BASE}/api/Settings/GetAll",
        "sumario_afonso_claudio": f"{BASE}/api/MunicipioControllers/Saude/GetSumario?anoExercicio=2026&idEsferaAdministrativa=1",
        "sumario_vitoria": f"{BASE}/api/MunicipioControllers/Saude/GetSumario?anoExercicio=2026&idEsferaAdministrativa=77",
        "evolucao_afonso_claudio": f"{BASE}/api/MunicipioControllers/Saude/GetGraficosEvolucaoAnualAplicacao?idEsferaAdministrativa=1&anoExercicio=2026",
    }

    for nome, url in testes.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            dados = resp.json()
            if nome == "settings":
                # a resposta completa e' enorme (uma entrada por municipio com
                # historico de prestacao de contas) - guarda so o resumo da
                # lista de esferas administrativas, que e' o que precisamos
                esferas = dados.get("esferasAdministrativas", [])
                resultado["testes"][nome] = {
                    "status_http": resp.status_code,
                    "total_esferas": len(esferas),
                    "amostra": [
                        {
                            "id": e.get("idEsferaAdministrativa"),
                            "codigo": e.get("codigoEsferaAdministrativa"),
                            "nome": e.get("nomeEsferaAdministrativa"),
                            "codigoIBGE": e.get("codigoIBGE"),
                        }
                        for e in esferas[:5]
                    ],
                }
            else:
                resultado["testes"][nome] = {"status_http": resp.status_code, "dados": dados}
        except Exception as e:  # noqa: BLE001
            resultado["erros"][nome] = str(e)[:500]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Teste de acesso: API REST do Painel de Controle TCE-ES ===")
    for nome in testes:
        if nome in resultado["erros"]:
            print(f"  [ERRO] {nome}: {resultado['erros'][nome]}")
        else:
            print(f"  [OK] {nome}: HTTP {resultado['testes'][nome]['status_http']}")

    return 1 if resultado["erros"] else 0


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "teste_api_rest.json"
    sys.exit(main(saida))
