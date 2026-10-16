#!/usr/bin/env python3
"""
Extrai os dados do painel "Gastos com a funcao saude" do Painel de Controle
do TCE-ES, direto via HTTP (sem navegador). Duas fontes, ambas sem
sessao/cookie/token dinamico (so o que vai na URL/corpo da chamada):

1. Power BI "publicar na web" (consultas/*.json reenviadas ao endpoint
   interno do Power BI) - traz valor por habitante, populacao com/sem plano
   de saude privado, gasto por subfuncao, evolucao anual em R$.
2. API REST propria do Painel de Controle (paineldecontrole.tcees.tc.br/api)
   - descoberta em 16/10/2026 explorando a pagina publica
   /municipio/<ano>/<cidade>/gestaoFiscal/saude - traz o indicador oficial
   de "Limite constitucional" (percentual da receita aplicado em saude,
   EC29/LC141) por municipio e para o ES, que o Power BI desta pagina nao
   tem (nao ha campo de receita nas consultas Power BI capturadas).
   Testada e confirmada acessivel de IP de nuvem compartilhada (GitHub
   Actions) em 16/10/2026 - ver resultados/teste-api-rest-tce-es.json e
   testar_api_rest.py.

Como isso foi descoberto esta documentado em LEIA-ME.md e nos commits do
teste de acesso (testar_acesso.py) e do teste de replay (testar_replay.py).

Uso: python extrair.py [saida.json]
Saida: grava um JSON com os dados brutos decodificados de cada consulta
(ainda sem o formato final do site - isso fica a cargo de montar.py).
"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

import dsr

URL = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "0b4992ae-e680-4f0c-b307-83c889f69479"
PASTA_CONSULTAS = Path(__file__).parent / "consultas"

API_REST_BASE = "https://paineldecontrole.tcees.tc.br"
API_REST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{API_REST_BASE}/municipio/2026/afonso-claudio/gestaoFiscal/saude",
}
MUNICIPIOS_TCE = json.loads((Path(__file__).parent / "municipios_tce_es.json").read_text(encoding="utf-8"))["municipios"]

# Consultas que de fato importam para o dado publicado (as demais salvas em
# consultas/ sao auxiliares da interface: badges HTML, legendas, opcoes de
# filtro, min/max do mapa - uteis de referencia, nao para publicar).
#
# Duas consultas foram testadas em 15/10/2026 e descartadas por nao
# retornarem dado util nesta pagina/fato (continuam salvas em consultas/
# para referencia futura, caso alguma das outras 5 paginas do mesmo
# relatorio Power BI as use de forma diferente):
#   - "atualizado_em": a medida CustomLabels_VisualMunicipal_AlertLog_Right
#     (rotulo nativo "dados atualizados ate") voltou sempre nula fora do
#     contexto exato do visual que a usa no painel original.
#   - "gestao_estadual": mesma consulta de "mapa_aplicacao_por_municipio"
#     com o filtro de esfera administrativa invertido (em vez de excluir
#     Estado do ES/Consorcio, inclui so esses dois) - voltou vazia, ou
#     seja, a tabela de fatos desta pagina (FT_DespesaDotacaoMunicipio) so
#     tem lancamento por MUNICIPIO, sem gasto estadual direto associado.
CONSULTAS_RELEVANTES = [
    "kpi_aplicacao_total",
    "kpi_valor_medio_habitante",
    "kpi_populacao_com_plano",
    "kpi_percentual_pop_com_plano",
    "evolucao_por_ano",
    "tabela_valor_medio_por_municipio",
    "tabela_aplicacao_por_subfuncao",
    "percentual_pop_sem_plano_por_municipio",
    "filtro_mes_min_max",
    "mapa_aplicacao_por_municipio",
    "evolucao_por_ano_municipio",
]


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


def substituir_ano(corpo: dict, ano: int) -> dict:
    """Troca o ano de referencia (ex.: "2026L") no corpo da consulta, se
    houver algum filtro desse tipo. Preserva o restante do corpo intacto."""
    texto = json.dumps(corpo)
    # os filtros de ano aparecem como {"Literal":{"Value":"2026L"}} dentro do
    # "Where" da consulta - troca qualquer ano de 4 digitos seguido de "L"
    import re

    texto_novo = re.sub(r'"\d{4}L"', f'"{ano}L"', texto)
    return json.loads(texto_novo)


def executar_consulta(nome: str, ano: int | None) -> dict:
    caminho = PASTA_CONSULTAS / f"{nome}.json"
    corpo = json.loads(caminho.read_text(encoding="utf-8"))
    if ano is not None:
        corpo = substituir_ano(corpo, ano)

    resp = requests.post(URL, headers=montar_headers(), json=corpo, timeout=30)
    resp.raise_for_status()
    dados_brutos = resp.json()
    decodificado = dsr.decodificar_resposta(dados_brutos)
    return decodificado


def get_api_rest(caminho: str, params: dict) -> dict:
    resp = requests.get(f"{API_REST_BASE}{caminho}", headers=API_REST_HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def extrair_limite_constitucional(ano: int) -> dict:
    """Extrai o indicador oficial de limite constitucional (EC29/LC141) de
    aplicacao em saude, da API REST propria do Painel de Controle: o
    percentual da receita aplicado em saude, para o ES e para cada um dos
    78 municipios, mais a evolucao anual (2022-ano) do valor e do
    percentual. Nao depende das consultas Power BI acima."""
    resultado = {"estado": None, "municipios": {}, "erros": {}}

    try:
        resultado["estado"] = get_api_rest("/api/EstadoControllers/Saude/GetSumario", {"anoExercicio": ano})
    except Exception as e:  # noqa: BLE001
        resultado["erros"]["estado"] = str(e)[:300]

    for m in MUNICIPIOS_TCE:
        nome = m["nome"]
        try:
            sumario = get_api_rest(
                "/api/MunicipioControllers/Saude/GetSumario",
                {"anoExercicio": ano, "idEsferaAdministrativa": m["id"]},
            )
            evolucao = get_api_rest(
                "/api/MunicipioControllers/Saude/GetGraficosEvolucaoAnualAplicacao",
                {"idEsferaAdministrativa": m["id"], "anoExercicio": ano},
            )
            resultado["municipios"][nome] = {"sumario": sumario, "evolucao": evolucao}
        except Exception as e:  # noqa: BLE001
            resultado["erros"][nome] = str(e)[:300]

    return resultado


def main(out_path: str, ano: int | None) -> int:
    resultado = {
        "quando_utc": datetime.now(timezone.utc).isoformat(),
        "ano_referencia": ano,
        "consultas": {},
        "erros": {},
    }

    for nome in CONSULTAS_RELEVANTES:
        try:
            resultado["consultas"][nome] = executar_consulta(nome, ano)
        except Exception as e:  # noqa: BLE001
            resultado["erros"][nome] = str(e)[:500]

    ano_limite = ano or datetime.now().year
    resultado["limite_constitucional"] = extrair_limite_constitucional(ano_limite)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Extracao: Gastos com a funcao saude (TCE-ES) ===")
    print(f"Ano de referencia: {ano}")
    for nome in CONSULTAS_RELEVANTES:
        if nome in resultado["erros"]:
            print(f"  [ERRO] {nome}: {resultado['erros'][nome]}")
        else:
            n = len(resultado["consultas"][nome]["linhas"])
            print(f"  [OK] {nome}: {n} linha(s)")

    lc = resultado["limite_constitucional"]
    print(f"Limite constitucional (API REST): estado {'OK' if lc['estado'] else 'ERRO'}, "
          f"{len(lc['municipios'])} municipio(s) OK, {len(lc['erros'])} erro(s)")

    erros_consultas = 1 if resultado["erros"] else 0
    erros_limite = 1 if lc["erros"] else 0
    return 1 if (erros_consultas or erros_limite) else 0


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "dados_extraidos.json"
    ano_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(main(saida, ano_arg))
