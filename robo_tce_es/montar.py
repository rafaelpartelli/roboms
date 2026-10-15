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

    # ---------------- Gasto por subfunção ----------------
    subfuncoes = []
    for linha in C["tabela_aplicacao_por_subfuncao"]["linhas"]:
        nome = linha.get("DIM_ClassificacaoFuncionalMunicipio.NomeSubFuncao")
        if nome is None:  # primeira linha é o agregado do ES, não uma subfunção
            continue
        subfuncoes.append([nome, num(linha.get("Formulas._SomaLiquidado")), num(linha.get("Formulas._SomaLiquidada RotuloAnoAnterior Perc__"))])
    subfuncoes.sort(key=lambda x: -(x[1] or 0))

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
    nomes = sorted(set(valor_mun) | set(plano_mun))
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
            )
        )
    municipios.sort(key=lambda m: -(m["valorHab"] or 0))

    D = dict(
        meta=dict(
            extracao=dt.datetime.fromisoformat(R["quando_utc"].replace("Z", "+00:00"))
            .astimezone(dt.timezone(dt.timedelta(hours=-3)))
            .strftime("%d/%m/%Y %H:%M"),
            anoRef=anoRef,
            fonte="Painel de Controle do TCE-ES (paineldecontrole.tcees.tc.br), Gastos com a função saúde",
        ),
        es=dict(
            aplicacao=aplicacao,
            aplicacaoLY=aplicacaoLY,
            valorHab=valorHab,
            valorHabLY=valorHabLY,
            percComPlano=percComPlano,
            popComPlano=popComPlano,
            evolucao=evolucao,
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
