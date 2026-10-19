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

    # ---------------- Limite constitucional (EC29/LC141) + série histórica de 8 anos ----------------
    # API REST própria do Painel de Controle (paineldecontrole.tcees.tc.br/api,
    # não Power BI). Traz o indicador oficial de limite constitucional
    # (percentual da receita aplicado em saúde, distinto do "percAplicado"
    # acima, que é fatia do gasto total do ES) e, desde 19/10/2026, uma série
    # histórica de 8 anos (a contar do ano mais recente, ex.: 2019-2026) com
    # TODOS os campos que a fonte devolve por ano: valor liquidado
    # ("aplicacao"), valor declarado pelo município ("valorDeclarado" — pode
    # diferir do liquidado em anos já encerrados, por retificação/auditoria;
    # mantido separado, nunca somado nem escolhido um no lugar do outro),
    # valor por habitante, ranking oficial do TCE-ES (por valor total e por
    # habitante) e, a nível de ES, a média de referência por município
    # ("participacaoMunicipal"/"PerCapita" — mesma para todos os municípios
    # num mesmo ano, por isso tratada como valor único do ES, não por
    # município). Fonte: extrair_serie_historica_rest() em extrair.py.
    # Degradação graciosa: ano sem dado (erro pontual na extração) fica de
    # fora da série, sem travar o restante.
    def receita_calculada(valor_liquidado, percentual):
        """Receita (arrecadação) não é devolvida pronta pela API — só o
        percentual já calculado. Como percentual = liquidado / receita * 100,
        a receita é obtida por cálculo direto a partir dos dois valores que a
        própria fonte declara (não é dado novo nem estimado por fora). Fica
        marcada como "calculada" na página; tem pequena imprecisão de
        arredondamento (percentual vem com 2 casas)."""
        if valor_liquidado is None or not percentual:
            return None
        return valor_liquidado / (percentual / 100)

    sh = R.get("serie_historica_rest") or {}
    anos_historico = R.get("anos_historico") or []
    ano_mais_recente = anos_historico[-1] if anos_historico else None

    estado_por_ano = sh.get("estado_por_ano") or {}
    municipios_por_ano = sh.get("municipios_por_ano") or {}

    # média de referência por município do ES, por ano (mesmo valor em todos
    # os municípios do mesmo ano na fonte — ver nota acima) - pega de
    # qualquer município disponível naquele ano
    media_mun_por_ano = {}
    for mapa_anos in municipios_por_ano.values():
        for ano_str, dado in mapa_anos.items():
            if ano_str not in media_mun_por_ano:
                media_mun_por_ano[ano_str] = (
                    num(dado.get("participacaoMunicipal")),
                    num(dado.get("participacaoPerCapitaMunicipal")),
                )

    historicoEstado = []
    for ano in anos_historico:
        e = estado_por_ano.get(str(ano))
        if not e:
            continue
        media_valor, media_per_capita = media_mun_por_ano.get(str(ano), (None, None))
        historicoEstado.append(
            [ano, num(e.get("aplicacao")), num(e.get("aplicacaoPercentual")), num(e.get("aplicacaoPerCapita")), media_valor, media_per_capita]
        )

    limiteEstado = None
    e_atual = estado_por_ano.get(str(ano_mais_recente)) if ano_mais_recente else None
    if e_atual:
        percEstado = num(e_atual.get("aplicacaoPercentual"))
        aplicacaoEstado = num(e_atual.get("aplicacao"))
        limiteEstado = dict(
            percentual=percEstado,
            aplicacao=aplicacaoEstado,
            aplicacaoPerCapita=num(e_atual.get("aplicacaoPerCapita")),
            populacao=e_atual.get("populacao"),
            receitaCalculada=receita_calculada(aplicacaoEstado, percEstado),
            # [ano, aplicacao, percentual, perCapita, participacaoMediaMunicipal, participacaoPerCapitaMediaMunicipal]
            historico=historicoEstado or None,
        )

    for m in municipios:
        mapa_anos = municipios_por_ano.get(m["n"]) or {}
        atual = mapa_anos.get(str(ano_mais_recente)) if ano_mais_recente else None
        if not atual:
            m["limitePercentual"] = None
            m["limiteValorLiquidado"] = None
            m["limiteValorDeclarado"] = None
            m["limiteReceitaCalculada"] = None
            m["limiteRanking"] = None
            m["limiteRankingPerCapita"] = None
            m["historico"] = None
            continue
        m["limitePercentual"] = num(atual.get("aplicacaoPercentual"))
        m["limiteValorLiquidado"] = num(atual.get("aplicacao"))
        m["limiteValorDeclarado"] = num(atual.get("valorDeclarado"))
        m["limiteReceitaCalculada"] = receita_calculada(m["limiteValorLiquidado"], m["limitePercentual"])
        m["limiteRanking"] = atual.get("rankingMunicipal")
        m["limiteRankingPerCapita"] = atual.get("rankingPerCapitaMunicipal")

        # [ano, aplicacao, valorDeclarado, percentual, perCapita, rankingAplicacao, rankingPerCapita]
        historico = []
        for ano in anos_historico:
            d = mapa_anos.get(str(ano))
            if not d:
                continue
            historico.append(
                [
                    ano,
                    num(d.get("aplicacao")),
                    num(d.get("valorDeclarado")),
                    num(d.get("aplicacaoPercentual")),
                    num(d.get("aplicacaoPerCapita")),
                    d.get("rankingMunicipal"),
                    d.get("rankingPerCapitaMunicipal"),
                ]
            )
        m["historico"] = historico or None

    # ---------------- Gasto por subfunção, por município (Power BI) ----------------
    # Mesma consulta usada para o panorama do ES (tabela_aplicacao_por_subfuncao),
    # com o filtro de município acrescentado em extrair.py (descoberto e
    # validado em 19/10/2026 - ver LEIA-ME.md e resultados/teste-subfuncao-municipio.json).
    # Degradação graciosa: município sem dado nessa execução fica com None
    # (a página volta a mostrar o panorama do ES para esse caso).
    subfuncao_mun_bruta = (R.get("subfuncao_por_municipio") or {}).get("municipios") or {}
    for m in municipios:
        linhas = subfuncao_mun_bruta.get(m["n"])
        if not linhas:
            m["subfuncoes"] = None
            continue
        subfuncoes_mun = [[nome_sub, num(valor)] for nome_sub, valor in linhas if nome_sub]
        subfuncoes_mun.sort(key=lambda x: -(x[1] or 0))
        m["subfuncoes"] = subfuncoes_mun or None

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
            anosHistorico=anos_historico or None,
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

    # Série histórica (API REST, 8 anos): checagem tolerante - falhas
    # pontuais num ano ou município não travam a publicação (degradação
    # graciosa, já tratada em montar()); só falha se a fonte da série
    # histórica caiu quase por completo nesta execução.
    anos_hist = D["meta"].get("anosHistorico") or []
    com_historico = sum(1 for m in D["m"] if m.get("historico"))
    if len(anos_hist) < 6:
        erros.append(f"série histórica com poucos anos: {len(anos_hist)} (esperado 8)")
    if com_historico < 60:
        erros.append(f"série histórica ausente na maioria dos municípios: só {com_historico}/{len(D['m'])} com dado")

    # Subfunção por município (Power BI, filtro por esfera administrativa):
    # mesma lógica tolerante - município sem dado volta a mostrar o
    # panorama do ES na página, não trava a publicação.
    com_subfuncao_mun = sum(1 for m in D["m"] if m.get("subfuncoes"))
    if com_subfuncao_mun < 60:
        erros.append(f"subfunção por município ausente na maioria dos municípios: só {com_subfuncao_mun}/{len(D['m'])} com dado")

    if erros:
        raise SystemExit("VALIDAÇÃO FALHOU: " + "; ".join(erros))
    return dict(
        aplicacao=round(D["es"]["aplicacao"]),
        valorHab=round(D["es"]["valorHab"], 2),
        municipios=len(D["m"]),
        anosHistorico=anos_hist,
        municipiosComHistorico=com_historico,
        municipiosComSubfuncao=com_subfuncao_mun,
    )


if __name__ == "__main__":
    R = json.load(open(sys.argv[1], encoding="utf-8"))
    D = montar(R)
    print("conferência:", validar(D))
    json.dump(D, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
