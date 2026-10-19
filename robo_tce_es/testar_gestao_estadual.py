#!/usr/bin/env python3
"""Teste pontual (19/10/2026, pedido do Rafael): varias consultas do painel
(kpi_aplicacao_total, evolucao_por_ano, kpi_valor_medio_habitante,
tabela_aplicacao_por_subfuncao) excluem explicitamente duas entidades da
dimensao DIM_EsferaAdministrativa.Nome: 'Estado do Espirito Santo' e
'Consorcio do Estado do Espirito Santo' (ver Where com "Not In"). Isso so
faz sentido se essas entidades tiverem registro proprio na tabela de fatos
(senao nao haveria nada para excluir). A investigacao anterior
(15-16/10/2026, ver LEIA-ME.md) tentou uma consulta diferente
(gestao_estadual.json, medindo Sum(FT_DespesaDotacaoMunicipio.Liquidada)
direto, sem passar pela medida DAX "Formulas._SomaLiquidado") e voltou
vazia. Este teste troca o "Not In" dessas consultas por um "In" explicito
para cada uma das duas entidades, mantendo a mesma medida
Formulas._SomaLiquidado ja usada (e validada) nas demais consultas, para
ver se agora aparece dado real."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import requests
import dsr

URL = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "0b4992ae-e680-4f0c-b307-83c889f69479"
CONSULTAS = Path(__file__).parent / "consultas"

ENTIDADES = ["Estado do Espírito Santo", "Consórcio do Estado do Espírito Santo"]


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


def substituir_not_in_por_in(where: list, alias_dim: str, entidade: str) -> list:
    """Acha a condicao 'Not In d.Nome [...]' e troca por 'In d.Nome [entidade]'."""
    novo = []
    achou = False
    for cond in where:
        c = cond.get("Condition", {})
        not_expr = c.get("Not", {}).get("Expression", {}).get("In")
        if not_expr:
            src = not_expr["Expressions"][0]["Column"]["Expression"]["SourceRef"]["Source"]
            prop = not_expr["Expressions"][0]["Column"]["Property"]
            if src == alias_dim and prop == "Nome":
                achou = True
                novo.append({
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {"Column": {"Expression": {"SourceRef": {"Source": alias_dim}}, "Property": "Nome"}}
                            ],
                            "Values": [[{"Literal": {"Value": f"'{entidade}'"}}]],
                        }
                    }
                })
                continue
        novo.append(cond)
    if not achou:
        raise RuntimeError(f"Not In d.Nome nao encontrado (alias esperado: {alias_dim})")
    return novo


def rodar(nome_consulta: str, alias_dim: str, entidade: str) -> dict:
    corpo = json.loads((CONSULTAS / f"{nome_consulta}.json").read_text(encoding="utf-8"))
    query = corpo["queries"][0]["Query"]["Commands"][0]["SemanticQueryDataShapeCommand"]["Query"]
    query["Where"] = substituir_not_in_por_in(query["Where"], alias_dim, entidade)
    resp = requests.post(URL, headers=montar_headers(), json=corpo, timeout=30)
    resp.raise_for_status()
    decodificado = dsr.decodificar_resposta(resp.json())
    return {"consulta": nome_consulta, "entidade": entidade, "linhas": decodificado["linhas"], "avisos": decodificado["avisos"]}


if __name__ == "__main__":
    resultado = []
    testes = [
        ("kpi_aplicacao_total", "d"),
        ("evolucao_por_ano", "d"),
        ("kpi_valor_medio_habitante", "d"),
        ("tabela_aplicacao_por_subfuncao", "d1"),
    ]
    for nome_consulta, alias_dim in testes:
        for entidade in ENTIDADES:
            try:
                r = rodar(nome_consulta, alias_dim, entidade)
            except Exception as e:  # noqa: BLE001
                r = {"consulta": nome_consulta, "entidade": entidade, "erro": str(e)[:500]}
            resultado.append(r)
            print(json.dumps(r, ensure_ascii=False)[:500])

    with open(str(Path(__file__).parent / "resultado_gestao_estadual.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
