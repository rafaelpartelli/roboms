"""
Decodificador do formato "DSR" (Data Shape Result) usado pelas respostas da
API interna do Power BI (endpoint "querydata").

O Power BI comprime as linhas de uma tabela: cada linha so lista no campo "C"
os valores que MUDARAM em relacao a linha anterior. Duas mascaras de bits
dizem o que fazer com cada posicao de coluna que nao esta em "C":

  - "R" (repete): a posicao usa o mesmo valor da linha anterior.
  - "Ø" (nulo): a posicao e nula nesta linha (ex.: variacao percentual do
    primeiro ano de uma serie, que nao tem ano anterior para comparar).

A primeira linha de uma tabela normalmente traz "S" (schema), uma lista com
o nome de cada posicao de coluna (ex.: G0 = chave de agrupamento, M0/M1/M2 =
medidas, na ordem em que aparecem no "Select" do pedido). Esse esquema vale
ate a proxima linha que trouxer um novo "S".

Validado manualmente contra o grafico "Evolucao valor aplicado em saude"
(anos 2020 a 2026) do painel "Gastos com a funcao saude" do TCE-ES: os
valores decodificados batem com o que a tela mostra.
"""
from __future__ import annotations


def decodificar_linhas(ph: dict) -> list[dict]:
    """Decodifica as linhas de um "PH" (physical holder) do DSR.

    Retorna uma lista de dicionarios {nome_da_posicao: valor}, por exemplo
    {"G0": 2020, "M0": None, "M1": "2803482357.809998", "M2": "R$ ...Bi"}.
    Os nomes de posicao (G0, M0, M1...) sao mapeados para os nomes reais das
    medidas/colunas em `mapear_posicoes_para_nomes`.
    """
    chave_linhas = next((k for k in ph if k.startswith("DM")), None)
    if chave_linhas is None:
        return []

    linhas_brutas = ph[chave_linhas]
    linhas_decodificadas: list[dict] = []
    schema_atual: list[str] = []
    anterior: list = []

    for linha in linhas_brutas:
        if "S" in linha:
            schema_atual = [col["N"] for col in linha["S"]]
            anterior = [None] * len(schema_atual)

        n = len(schema_atual)
        bitmask_repete = linha.get("R", 0)
        bitmask_nulo = linha.get("Ø", 0)  # "Ø"
        valores_c = linha.get("C", [])
        idx_c = 0
        atual = [None] * n

        for pos in range(n):
            bit = 1 << pos
            if bitmask_repete & bit:
                atual[pos] = anterior[pos] if pos < len(anterior) else None
            elif bitmask_nulo & bit:
                atual[pos] = None
            else:
                atual[pos] = valores_c[idx_c] if idx_c < len(valores_c) else None
                idx_c += 1

        linhas_decodificadas.append(dict(zip(schema_atual, atual)))
        anterior = atual

    return linhas_decodificadas


def mapear_posicoes_para_nomes(descriptor: dict) -> dict[str, str]:
    """Mapeia posicoes (G0, M0, M1...) para o nome real da coluna/medida,
    usando o "Select" do descriptor da resposta (cada item tem "Value" com a
    posicao e "Name" com o nome real, ex.: Formulas._SomaLiquidado)."""
    mapa = {}
    for item in descriptor.get("Select", []):
        if not item:
            continue
        pos = item.get("Value")
        nome = item.get("Name")
        if pos and nome:
            mapa[pos] = nome
    return mapa


def decodificar_resposta(corpo_resposta: dict) -> dict:
    """Decodifica uma resposta completa de /public/reports/querydata.

    Retorna um dicionario com:
      - "linhas": lista de linhas, cada uma com os nomes reais das colunas
        (ja traduzidos de G0/M0/... para o nome da medida/coluna)
      - "valores_unicos": valores que ficam no nivel do DS0 (fora das linhas,
        ex.: o maximo do eixo Y de um grafico), tambem com nome traduzido
        quando possivel
      - "aviso": mensagens de aviso que o Power BI retornou (ex.: algoritmo
        de reducao de dados ignorado), uteis para saber se a consulta trouxe
        TODAS as linhas ou foi cortada
    """
    resultado = corpo_resposta["results"][0]["result"]
    dados = resultado["data"]
    descriptor = dados.get("descriptor", {})
    mapa_nomes = mapear_posicoes_para_nomes(descriptor)

    dsr = dados.get("dsr", {})
    ds0 = dsr.get("DS", [{}])[0]

    linhas = []
    for ph in ds0.get("PH", []):
        for linha in decodificar_linhas(ph):
            linha_traduzida = {mapa_nomes.get(k, k): v for k, v in linha.items()}
            linhas.append(linha_traduzida)

    valores_unicos = {}
    for k, v in ds0.items():
        if k in ("N", "S", "PH", "IC", "HAD", "Msg"):
            continue
        valores_unicos[mapa_nomes.get(k, k)] = v

    avisos = [m.get("Message", "") for m in ds0.get("Msg", [])]

    return {"linhas": linhas, "valores_unicos": valores_unicos, "avisos": avisos}
