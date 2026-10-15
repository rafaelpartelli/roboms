#!/usr/bin/env python3
"""
Teste de REPLAY direto (sem navegador) da chamada de dados do Power BI.

O teste anterior (testar_acesso.py) provou que o Painel de Controle do TCE-ES
usa um relatorio Power BI "publicar na web" e capturou, via Playwright, o
corpo exato de uma chamada "querydata". Analisando esse corpo, descobrimos
que ele carrega seus proprios identificadores (DatasetId, ReportId, VisualId,
modelId) e so usa dois cabecalhos de correlacao (requestid/activityid) que
sao gerados livremente pelo cliente - ou seja, a chamada nao depende de
sessao, cookie ou token dinamico.

Este script testa se isso e verdade: reenvia o MESMO corpo capturado (fixture
em consultas/aplicacao_saude_total.json), gerando novos requestid/activityid,
usando so a biblioteca "requests" (sem Playwright, sem navegador). Se der
200 com dados validos, confirma que o robo definitivo pode rodar sem precisar
abrir um navegador a cada execucao - mais rapido, mais leve, mais confiavel.

Uso: python testar_replay.py [saida.json]
"""
import json
import sys
import uuid
from datetime import datetime, timezone

import requests

URL = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "0b4992ae-e680-4f0c-b307-83c889f69479"


def montar_headers() -> dict:
    return {
        "x-powerbi-resourcekey": RESOURCE_KEY,
        "requestid": str(uuid.uuid4()),
        "activityid": str(uuid.uuid4()),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
        "referer": "https://app.powerbi.com/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }


def main(out_path: str) -> int:
    with open("consultas/kpi_aplicacao_total.json", "r", encoding="utf-8") as f:
        corpo = json.load(f)

    resultado = {
        "quando_utc": datetime.now(timezone.utc).isoformat(),
        "url": URL,
        "status_http": None,
        "corpo_resposta": None,
        "valor_extraido": None,
        "erro": None,
        "veredito": None,
    }

    try:
        resp = requests.post(URL, headers=montar_headers(), json=corpo, timeout=30)
        resultado["status_http"] = resp.status_code
        resp.raise_for_status()
        dados = resp.json()
        resultado["corpo_resposta"] = dados

        # navega ate o valor escalar (mesma estrutura DSR vista no teste anterior):
        # results[0].result.data.dsr.DS[0].PH[0].DM0[0].M0  (ou similar, conforme a query)
        dsr = dados["results"][0]["result"]["data"]["dsr"]
        dm0 = dsr["DS"][0]["PH"][0]["DM0"][0]
        resultado["valor_extraido"] = dm0
        resultado["veredito"] = "REPLAY_OK"
    except Exception as e:  # noqa: BLE001
        resultado["erro"] = str(e)[:500]
        resultado["veredito"] = "REPLAY_FALHOU"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Teste de replay direto (sem navegador) da chamada Power BI ===")
    print(f"HTTP: {resultado['status_http']}")
    print(f"Valor extraido: {resultado['valor_extraido']}")
    if resultado["erro"]:
        print(f"Erro: {resultado['erro']}")
    print(f"VEREDITO: {resultado['veredito']}")

    return 0 if resultado["veredito"] == "REPLAY_OK" else 1


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "resultado_replay.json"
    sys.exit(main(saida))
