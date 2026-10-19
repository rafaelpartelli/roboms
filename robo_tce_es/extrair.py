#!/usr/bin/env python3
"""
Extrai os dados do painel "Gastos com a funcao saude" do Painel de Controle
do TCE-ES, direto via HTTP (sem navegador). Duas fontes, ambas sem
sessao/cookie/token dinamico (so o que vai na URL/corpo da chamada):

1. Power BI "publicar na web" (consultas/*.json reenviadas ao endpoint
   interno do Power BI) - traz valor por habitante, populacao com/sem plano
   de saude privado, gasto por subfuncao, evolucao anual em R$ (dataset do
   proprio relatorio so cobre 2020 em diante).
2. API REST propria do Painel de Controle (paineldecontrole.tcees.tc.br/api)
   - descoberta em 16/10/2026 explorando a pagina publica
   /municipio/<ano>/<cidade>/gestaoFiscal/saude - traz o indicador oficial
   de "Limite constitucional" (percentual da receita aplicado em saude,
   EC29/LC141), alem de valor liquidado, valor declarado, valor per capita
   e ranking oficial do TCE-ES, por municipio e para o ES. Testada e
   confirmada acessivel de IP de nuvem compartilhada (GitHub Actions) em
   16/10/2026 - ver resultados/teste-api-rest-tce-es.json e
   testar_api_rest.py.

   Serie historica (19/10/2026): testamos (testar_historico.py, resultado em
   resultados/teste-historico-tce-es.json) e confirmamos que GetSumario tem
   dado real desde pelo menos 2015 - diferente de GetGraficosEvolucaoAnualAplicacao,
   que so devolve uma janela fixa de 5 anos terminando no ano pedido (nao
   acumula historico maior). Por isso extrair_serie_historica_rest() abaixo
   chama GetSumario uma vez por ano, para o ES e cada um dos 78 municipios,
   trazendo TODOS os campos que a API devolve (aplicacao, valorDeclarado,
   aplicacaoPercentual, aplicacaoPerCapita, participacaoMunicipal,
   participacaoPerCapitaMunicipal, rankingMunicipal, rankingPerCapitaMunicipal),
   e GetGraficosEvolucaoAnualAplicacao deixou de ser chamado (superado pela
   serie ano a ano, mais completa e com mais anos).

Como isso foi descoberto esta documentado em LEIA-ME.md e nos commits do
teste de acesso (testar_acesso.py) e do teste de replay (testar_replay.py).

Uso: python extrair.py [saida.json] [ano_mais_recente]
Saida: grava um JSON com os dados brutos decodificados de cada consulta
(ainda sem o formato final do site - isso fica a cargo de montar.py).
"""
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Serie historica da API REST: 8 anos a contar do ano atual, incluindo o
# ano atual (ex.: em 2026, cobre 2019-2026). Pedido do Rafael em 19/10/2026.
JANELA_HISTORICO_ANOS = 8

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


def get_api_rest(caminho: str, params: dict, tentativas: int = 3) -> dict:
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(f"{API_REST_BASE}{caminho}", headers=API_REST_HEADERS, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            ultimo_erro = e
            if tentativa < tentativas:
                time.sleep(1.5 * tentativa)  # backoff simples antes de tentar de novo
    raise ultimo_erro


def extrair_serie_historica_rest(anos: list[int]) -> dict:
    """Extrai, da API REST propria do Painel de Controle (/api/...), TODOS os
    campos que o GetSumario oficial devolve - aplicacao (valor liquidado),
    valorDeclarado, aplicacaoPercentual (indicador de limite constitucional
    EC29/LC141), aplicacaoPerCapita, participacaoMunicipal/PerCapita (media
    de referencia do ES) e rankingMunicipal/PerCapita (ranking oficial do
    TCE-ES) - para o ES e para cada um dos 78 municipios, em cada um dos
    anos pedidos (serie historica). Nao depende das consultas Power BI
    acima, nem mais chama GetGraficosEvolucaoAnualAplicacao (ver nota no
    topo do arquivo: essa consulta so devolve uma janela fixa de 5 anos,
    GetSumario ano a ano cobre mais e traz mais campos).

    Usa um pequeno pool de threads (a API nao tem autenticacao nem limite
    de requisicao documentado, mas e' gentil nao disparar tudo de uma vez
    so): ES + 78 municipios x 8 anos = 632 chamadas HTTP leves (JSON
    pequeno, sem decodificacao DSR)."""
    resultado = {"estado_por_ano": {}, "municipios_por_ano": {m["nome"]: {} for m in MUNICIPIOS_TCE}, "erros": {}}

    tarefas = []
    for ano in anos:
        tarefas.append(("estado", None, ano))
        for m in MUNICIPIOS_TCE:
            tarefas.append((m["nome"], m["id"], ano))

    def buscar_uma(tarefa):
        nome, id_esfera, ano = tarefa
        if nome == "estado":
            dado = get_api_rest("/api/EstadoControllers/Saude/GetSumario", {"anoExercicio": ano})
        else:
            dado = get_api_rest(
                "/api/MunicipioControllers/Saude/GetSumario",
                {"anoExercicio": ano, "idEsferaAdministrativa": id_esfera},
            )
        return nome, ano, dado

    with ThreadPoolExecutor(max_workers=6) as pool:
        futuros = {pool.submit(buscar_uma, t): t for t in tarefas}
        for futuro in as_completed(futuros):
            nome, id_esfera, ano = futuros[futuro]
            chave_erro = f"{nome}_{ano}"
            try:
                _, _, dado = futuro.result()
            except Exception as e:  # noqa: BLE001
                resultado["erros"][chave_erro] = str(e)[:300]
                continue
            if nome == "estado":
                resultado["estado_por_ano"][str(ano)] = dado
            else:
                resultado["municipios_por_ano"][nome][str(ano)] = dado

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

    ano_mais_recente = ano or datetime.now().year
    anos_historico = list(range(ano_mais_recente - JANELA_HISTORICO_ANOS + 1, ano_mais_recente + 1))
    resultado["anos_historico"] = anos_historico
    resultado["serie_historica_rest"] = extrair_serie_historica_rest(anos_historico)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Extracao: Gastos com a funcao saude (TCE-ES) ===")
    print(f"Ano de referencia (Power BI): {ano}")
    for nome in CONSULTAS_RELEVANTES:
        if nome in resultado["erros"]:
            print(f"  [ERRO] {nome}: {resultado['erros'][nome]}")
        else:
            n = len(resultado["consultas"][nome]["linhas"])
            print(f"  [OK] {nome}: {n} linha(s)")

    sh = resultado["serie_historica_rest"]
    n_anos_estado_ok = len(sh["estado_por_ano"])
    n_pares_municipio_ok = sum(len(v) for v in sh["municipios_por_ano"].values())
    esperado_estado = len(anos_historico)
    esperado_municipios = len(anos_historico) * len(MUNICIPIOS_TCE)
    print(
        f"Serie historica REST ({anos_historico[0]}-{anos_historico[-1]}): "
        f"ES {n_anos_estado_ok}/{esperado_estado} ano(s) OK, "
        f"municipios {n_pares_municipio_ok}/{esperado_municipios} par(es) ano-municipio OK, "
        f"{len(sh['erros'])} erro(s)"
    )

    erros_consultas = 1 if resultado["erros"] else 0
    # tolera algumas falhas pontuais na serie historica (degradacao graciosa,
    # tratada em montar.py), so falha a extracao se faltar demais
    erros_serie_historica = 1 if len(sh["erros"]) > (esperado_estado + esperado_municipios) * 0.1 else 0
    return 1 if (erros_consultas or erros_serie_historica) else 0


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "dados_extraidos.json"
    ano_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(main(saida, ano_arg))
