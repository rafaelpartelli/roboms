#!/usr/bin/env python3
"""
Extrai os dados do painel "Gastos com a funcao saude" do Painel de Controle
do TCE-ES, direto via HTTP (sem navegador), reenviando as consultas
capturadas em `consultas/` ao endpoint interno do Power BI.

Como isso foi descoberto, e por que funciona sem sessao/cookie/token
dinamico, esta documentado em LEIA-ME.md e nos commits do teste de acesso
(testar_acesso.py) e do teste de replay (testar_replay.py).

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

# Consultas que de fato importam para o dado publicado (as demais salvas em
# consultas/ sao auxiliares da interface: badges HTML, legendas, opcoes de
# filtro, min/max do mapa - uteis de referencia, nao para publicar).
# "gestao_estadual" nao foi capturada da interface: e' a mesma consulta de
# "mapa_aplicacao_por_municipio" com o filtro de esfera administrativa
# invertido (em vez de excluir Estado do ES/Consorcio, inclui so esses dois).
CONSULTAS_RELEVANTES = [
    "kpi_aplicacao_total",
    "kpi_valor_medio_habitante",
    "kpi_populacao_com_plano",
    "kpi_percentual_pop_com_plano",
    "evolucao_por_ano",
    "tabela_valor_medio_por_municipio",
    "tabela_aplicacao_por_subfuncao",
    "percentual_pop_sem_plano_por_municipio",
    "atualizado_em",
    "filtro_mes_min_max",
    "mapa_aplicacao_por_municipio",
    "gestao_estadual",
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

    return 1 if resultado["erros"] else 0


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "dados_extraidos.json"
    ano_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(main(saida, ano_arg))
