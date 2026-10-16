#!/usr/bin/env python3
"""Transforma a extração bruta do Painel TCE-ES (bruto.json, saída de extrair.py)
no dados.json final da página "Painel TCE-ES: Gastos com a Função Saúde"
(partelli.pro/gestor/tce/). Segue o mesmo padrão do dados.json do Radar de
Recursos SUS (robo/montar.py): números já convertidos para float, percentuais
como fração (0-1), chaves curtas.

Uso: python3 montar.py bruto.json dados.json
"""
import json
import sys
import datetime as dt


def num(v):
    """Os valores do DSR chegam como string ou número; alguns None."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


MESES_PT = [
    None, "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


def periodo_legivel(mes_min, mes_max, ano):
    if mes_min is None or mes_max is None:
        return None
    if mes_min == mes_max:
        return f"{MESES_PT[mes_min]}/{ano}"
    return f"{MESES_PT[mes_min]} a {MESES_PT[mes_max]}/{ano}"


def montar(R):
    C = R["consultas"]

    # ---------------- KPIs gerais do ES ----------------
    kpi_apl = C["kpi_aplicacao_total"]["linhas"][0]
    kpi_hab = C["kpi_valor_medio_habitante"]["linhas"][0]
    kpi_pop = C["kpi_populacao_com_plano"]["linhas"][0]
    kpi_perc = C["kpi_percentual_pop_com_plano"]["linhas"][0]

    aplicacao = num(kpi_apl.get("Formulas._SomaLiquidado"))
    aplicacaoLY = num(kpi_apl.get("Formulas._SomaLiquidado LY"))
    valorHab = num(kpi_hab.get("Formulas._MediaLiquidadaPorHabitante"))
    valorHabLY = num(kpi_hab.get("Formulas._MediaLiquidadaPorHabitante LY"))
    percComPlano = num(kpi_perc.get("Formulas._MediaPercPopComPlano"))
    popComPlano = num(kpi_perc.get("Formulas._SomaPopulacaoComPlano")) or num(
        kpi_pop.get("Formulas._SomaPopulacaoComPlano_")
    )

    # ---------------- Evolução por ano (série do ES) ----------------
    evolucao = []
    for linha in C["evolucao_por_ano"]["linhas"]:
        ano = linha.get("FT_DespesaDotacaoMunicipio.AnoReferencia")
        if ano is None:
            continue
        evolucao.append(
            [int(ano), num(linha.get("Formulas._SomaLiquidado")), num(linha.get("Formulas._SomaLiquidado YoY %"))]
        )
    evolucao.sort(key=lambda x: x[0])
    anoRef = evolucao[-1][0] if evolucao else None

    # ---------------- Evolução por ano, por município ----------------
    evolucao_mun = {}
    if C.get("evolucao_por_ano_municipio", {}).get("linhas"):
        for linha in C["evolucao_por_ano_municipio"]["linhas"]:
            ano = linha.get("FT_DespesaDotacaoMunicipio.AnoReferencia")
            nome = linha.get("DIM_EsferaAdministrativa.Nome")
            if ano is None or nome is None:
                continue
            evolucao_mun.setdefault(nome, []).append(
                [int(ano), num(linha.get("Formulas._SomaLiquidado")), num(linha.get("Formulas._SomaLiquidado YoY %"))]
            )
        for lista in evolucao_mun.values():
            lista.sort(key=lambda x: x[0])

    # ---------------- Gasto por subfunção ----------------
    subfuncoes = []
    for linha in C["tabela_aplicacao_por_subfuncao"]["linhas"]:
        nome = linha.get("DIM_ClassificacaoFuncionalMunicipio.NomeSubFuncao")
        if nome is None:  # primeira linha é o agregado do ES, não uma subfunção
            continue
        subfuncoes.append([nome, num(linha.get("Formulas._SomaLiquidado")), num(linha.get("Formulas._SomaLiquidada RotuloAnoAnterior Perc__"))])
    subfuncoes.sort(key=lambda x: -(x[1] or 0))

    # ---------------- Período em análise (mês mínimo/máximo do ano) ----------------
    mes_min = mes_max = None
    if C.get("filtro_mes_min_max", {}).get("linhas"):
        linha_mes = C["filtro_mes_min_max"]["linhas"][0]
        mes_min = linha_mes.get("Min(FT_DespesaDotacaoMunicipio.MesReferencia)")
        mes_max = linha_mes.get("Max(FT_DespesaDotacaoMunicipio.MesReferencia)")
        mes_min = int(mes_min) if mes_min is not None else None
        mes_max = int(mes_max) if mes_max is not None else None

    # ---------------- Valor bruto aplicado, por município (para % do total) ----------------
    aplicado_mun = {}
    if C.get("mapa_aplicacao_por_municipio", {}).get("linhas"):
        for linha in C["mapa_aplicacao_por_municipio"]["linhas"]:
            nome = linha.get("DIM_EsferaAdministrativa.Nome")
            if nome is None:
                continue
            aplicado_mun[nome] = num(linha.get("Sum(FT_DespesaDotacaoMunicipio.Liquidada)"))

    # ---------------- Valor médio por habitante, por município ----------------
    valor_mun = {}
    for linha in C["tabela_valor_medio_por_municipio"]["linhas"]:
        nome = linha.get("DIM_EsferaAdministrativa.Nome")
        if nome is None:  # primeira linha é o agregado do ES
            continue
        valor_mun[nome] = {
            "valorHab": num(linha.get("Formulas._MediaLiquidadaPorHabitante")),
            "varHab": num(linha.get("Formulas._ValorMedioPorHabitante RotuloAnoAnterior Perc__")),
        }

    # ---------------- Cobertura de plano de saúde privado, por município ----------------
    plano_mun = {}
    for linha in C["percentual_pop_sem_plano_por_municipio"]["linhas"]:
        nome = linha.get("DIM_EsferaAdministrativa.Nome")
        if nome is None:
            continue
        pop = linha.get("Sum(Populacao.Populacao)")
        benef = linha.get("Sum(saude Beneficiario.Beneficiarios)")
        plano_mun[nome] = {
            "pop": pop,
            "benef": benef,
            "percSemPlano": num(linha.get("Formulas._PercPopSemPlano")),
            "percSemPlanoYoY": num(linha.get("Formulas._PercPopSemPlano YoY")),
        }

    # ---------------- Junta num único registro por município ----------------
    nomes = sorted(set(valor_mun) | set(plano_mun) | set(aplicado_mun))
    municipios = []
    for nome in nomes:
        v = valor_mun.get(nome, {})
        p = plano_mun.get(nome, {})
        pop = p.get("pop")
        benef = p.get("benef")
        percSemPlano = p.get("percSemPlano")
        percComPlanoMun = (benef / pop) if (pop and benef is not None) else (1 - percSemPlano if percSemPlano is not None else None)
        municipios.append(
            dict(
                n=nome,
                valorHab=v.get("valorHab"),
                varHab=v.get("varHab"),
                pop=pop,
                benef=benef,
                percComPlano=percComPlanoMun,
                percSemPlanoYoY=p.get("percSemPlanoYoY"),
                aplicado=aplicado_mun.get(nome),
                evolucao=evolucao_mun.get(nome) or None,
            )
        )
    municipios.sort(key=lambda m: -(m["valorHab"] or 0))

    # ---------------- Mínimo e máximo valor por habitante, com o município ----------------
    # Municípios excluídos apenas do destaque de maior/menor valor por habitante
    # no panorama geral dos 78: casos com distorção estrutural conhecida que não
    # refletem gestão de saúde (royalties de petróleo per capita, população muito
    # pequena etc.), a pedido do Rafael em 16/10/2026. Continuam normalmente na
    # tabela, no ranking e em todos os demais cálculos — só saem do "maior/menor"
    # do panorama geral.
    EXCLUIR_DOS_EXTREMOS_PANORAMA = {"Presidente Kennedy"}
    com_valor_hab = [
        m for m in municipios
        if m["valorHab"] is not None and m["n"] not in EXCLUIR_DOS_EXTREMOS_PANORAMA
    ]
    valorHabMin = valorHabMax = None
    valorHabMinMunicipio = valorHabMaxMunicipio = None
    if com_valor_hab:
        m_min = min(com_valor_hab, key=lambda m: m["valorHab"])
        m_max = max(com_valor_hab, key=lambda m: m["valorHab"])
        valorHabMin, valorHabMinMunicipio = m_min["valorHab"], m_min["n"]
        valorHabMax, valorHabMaxMunicipio = m_max["valorHab"], m_max["n"]

    # percentual aplicado de cada município sobre o total do ES (soma dos
    # proprios municipios, que e' o denominador correto para "fatia no bolo
    # municipal" - o total do ES/aplicacao acima pode incluir outras esferas)
    total_aplicado_municipios = sum(m["aplicado"] for m in municipios if m["aplicado"] is not None) or None
    for m in municipios:
        m["percAplicado"] = (m["aplicado"] / total_aplicado_municipios) if (m["aplicado"] is not None and total_aplicado_municipios) else None

    # ---------------- Limite constitucional (EC29/LC141), API REST do TCE-ES ----------------
    # Percentual da receita aplicado em saude - indicador oficial, distinto
    # do "percAplicado" acima (que e' fatia do gasto total do ES, nao da
    # receita do proprio municipio). Fonte: extrair_limite_constitucional()
    # em extrair.py (API REST propria do Painel de Controle, nao Power BI).
    lc = R.get("limite_constitucional") or {}
    limiteEstado = None
    if lc.get("estado"):
        e = lc["estado"]
        limiteEstado = dict(
            percentual=num(e.get("aplicacaoPercentual")),
            aplicacao=num(e.get("aplicacao")),
            aplicacaoPerCapita=num(e.get("aplicacaoPerCapita")),
            populacao=e.get("populacao"),
        )

    limite_mun = lc.get("municipios") or {}
    for m in municipios:
        info = limite_mun.get(m["n"])
        if not info:
            m["limitePercentual"] = None
            m["limiteEvolucao"] = None
            continue
        sumario = info.get("sumario") or {}
        m["limitePercentual"] = num(sumario.get("aplicacaoPercentual"))
        evo = info.get("evolucao") or {}
        pontos_valor = {p["ano"]: num(p.get("valor")) for p in (evo.get("aplicacao") or [])}
        pontos_perc = {p["ano"]: num(p.get("valor")) for p in (evo.get("percentual") or [])}
        anos = sorted(set(pontos_valor) | set(pontos_perc))
        m["limiteEvolucao"] = [[a, pontos_valor.get(a), pontos_perc.get(a)] for a in anos] or None

    D = dict(
        meta=dict(
            extracao=dt.datetime.fromisoformat(R["quando_utc"].replace("Z", "+00:00"))
            .astimezone(dt.timezone(dt.timedelta(hours=-3)))
            .strftime("%d/%m/%Y %H:%M"),
            anoRef=anoRef,
            mesMin=mes_min,
            mesMax=mes_max,
            periodo=periodo_legivel(mes_min, mes_max, anoRef),
            fonte="Painel de Controle do TCE-ES (paineldecontrole.tcees.tc.br), Gastos com a função saúde",
        ),
        es=dict(
            aplicacao=aplicacao,
            aplicacaoLY=aplicacaoLY,
            valorHab=valorHab,
            valorHabLY=valorHabLY,
            valorHabMin=valorHabMin,
            valorHabMinMunicipio=valorHabMinMunicipio,
            valorHabMax=valorHabMax,
            valorHabMaxMunicipio=valorHabMaxMunicipio,
            percComPlano=percComPlano,
            popComPlano=popComPlano,
            evolucao=evolucao,
            limiteConstitucional=limiteEstado,
        ),
        subfuncoes=subfuncoes,
        m=municipios,
    )
    return D


def validar(D):
    """Checagens mínimas antes de publicar. Lança erro se algo estiver fora do esperado."""
    erros = []
    if not D["es"]["aplicacao"] or D["es"]["aplicacao"] <= 0:
        erros.append("aplicação total do ES zerada ou ausente")
    if not D["es"]["valorHab"] or D["es"]["valorHab"] <= 0:
        erros.append("valor médio por habitante do ES zerado ou ausente")
    if D["es"]["percComPlano"] is None or not (0 < D["es"]["percComPlano"] < 1):
        erros.append(f"percentual com plano fora do esperado: {D['es']['percComPlano']}")
    if len(D["m"]) < 70:
        erros.append(f"esperados pelo menos 70 municípios, vieram {len(D['m'])}")
    if len(D["subfuncoes"]) < 5:
        erros.append(f"poucas subfunções: {len(D['subfuncoes'])}")
    hoje = __import__("datetime").date.today().year
    if D["meta"]["anoRef"] and not (hoje - 1 <= D["meta"]["anoRef"] <= hoje + 1):
        erros.append(f"ano de referência fora do esperado: {D['meta']['anoRef']}")
    if erros:
        raise SystemExit("VALIDAÇÃO FALHOU: " + "; ".join(erros))
    return dict(aplicacao=round(D["es"]["aplicacao"]), valorHab=round(D["es"]["valorHab"], 2), municipios=len(D["m"]))


if __name__ == "__main__":
    R = json.load(open(sys.argv[1], encoding="utf-8"))
    D = montar(R)
    print("conferência:", validar(D))
    json.dump(D, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
