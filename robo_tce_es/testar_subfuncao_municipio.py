#!/usr/bin/env python3
"""Teste pontual: a tabela_aplicacao_por_subfuncao.json capturada so filtra
'fora Estado/Consorcio', sem recorte de municipio. No live Power BI,
selecionar um municipio no slicer "Esfera administrativa" atualiza essa
mesma tabela (visto ao vivo para Presidente Kennedy: total R$48,65 Mi bateu
com o KPI do municipio). Este teste adiciona um filtro IN d1.Nome = <municipio>
ao corpo da consulta capturada e reenvia, pra confirmar se da pra reproduzir
isso via HTTP puro (sem navegador)."""
import json
import sys
import uuid

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import requests
import dsr

URL = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "0b4992ae-e680-4f0c-b307-83c889f69479"


def montar_headers():
    return {
        "x-powerbi-resourcekey": RESOURCE_KEY,
        "requestid": str(uuid.uuid4()),
        "activityid": str(uuid.uuid4()),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
        "referer": "https://app.powerbi.com/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }


def main(municipio: str) -> dict:
    corpo = json.loads(open(str(__import__("pathlib").Path(__file__).parent / "consultas" / "tabela_aplicacao_por_subfuncao.json"), encoding="utf-8").read())
    query = corpo["queries"][0]["Query"]["Commands"][0]["SemanticQueryDataShapeCommand"]["Query"]
    filtro_municipio = {
        "Condition": {
            "In": {
                "Expressions": [
                    {"Column": {"Expression": {"SourceRef": {"Source": "d1"}}, "Property": "Nome"}}
                ],
                "Values": [[{"Literal": {"Value": f"'{municipio}'"}}]],
            }
        }
    }
    query["Where"].append(filtro_municipio)
    # mantem o resto do corpo intacto, so acrescenta o filtro

    resp = requests.post(URL, headers=montar_headers(), json=corpo, timeout=30)
    resp.raise_for_status()
    decodificado = dsr.decodificar_resposta(resp.json())
    subfuncoes = {}
    total = 0.0
    for linha in decodificado["linhas"]:
        nome = linha.get("DIM_ClassificacaoFuncionalMunicipio.NomeSubFuncao")
        valor = linha.get("Formulas._SomaLiquidado")
        if nome is None:
            continue
        v = float(valor) if valor is not None else 0.0
        subfuncoes[nome] = v
        total += v
    return {"municipio": municipio, "subfuncoes": subfuncoes, "total": total, "avisos": decodificado["avisos"]}


if __name__ == "__main__":
    municipios = sys.argv[1:] or ["Presidente Kennedy", "Vitória", "Afonso Cláudio"]
    resultado = [main(m) for m in municipios]
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    out_path = sys.argv[0].replace("testar_subfuncao_municipio.py", "") or "."
    with open((__import__("pathlib").Path(out_path) / "resultado_subfuncao_municipio.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
