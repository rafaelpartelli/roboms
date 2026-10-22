#!/usr/bin/env python3
"""Transforma a extração bruta do InvestSUS (bruto.json) no JSON de uma UF do Radar de Recursos SUS.

Uso: python3 montar.py bruto.json dados.json [--anterior publicado.json]
A UF vem do próprio arquivo bruto (campo "uf"). Com --anterior, compara com a última
publicação e recusa (código 1) variações suspeitas de saldo ou de fundo a fundo.
"""
import json, sys, statistics, unicodedata, pathlib, datetime as dt
from collections import defaultdict

# quantidade de municípios por UF (IBGE); a validação recusa extrações incompletas
ESPERADOS = {'ES': 78, 'MG': 853, 'MA': 217}
NOMES_IBGE = pathlib.Path(__file__).parent / 'municipios_ibge.json'


def sem_acento(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().upper()
    return ' '.join(s.replace("'", ' ').replace('-', ' ').split())


def nomes_oficiais(uf):
    """Mapa nome do painel (maiúsculo, sem acento) -> nome oficial do IBGE, e mapa de palavras acentuadas."""
    try:
        lista = json.loads(NOMES_IBGE.read_text(encoding='utf-8'))['ufs'].get(uf, [])
    except Exception:
        return {}, {}
    nomes = {sem_acento(n): n for n in lista}
    pal = defaultdict(set)
    for n in lista:
        for w in n.replace('-', ' ').split():
            b = sem_acento(w)
            if b != w.upper() and b.isalpha():
                pal[b].add(w.upper())
    acc = {k: next(iter(v)).capitalize() for k, v in pal.items() if len(v) == 1}
    return nomes, acc

MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
GRUPOS = ['CUSTEIO', 'INVESTIMENTO', 'EMENDAS', 'RIODOCE', 'ENFERMAGEM', 'OUTROS']
EST = 'EST'  # chave do Governo do Estado (Fundo Estadual de Saúde)


def grupo(tipo):
    """Agrupa o tipo de conta do FNS em categorias de gestão."""
    t = (tipo or '').upper()
    if t == 'EMENDA':
        return 'EMENDAS'
    if t.startswith('REPRBF'):
        return 'RIODOCE'
    if t == 'ENFERMAGEM':
        return 'ENFERMAGEM'
    if t in ('INVESTSUS', 'INVSUS', 'BLINV', 'INVAN', 'FARINV') or t.startswith('IN'):
        return 'INVESTIMENTO'
    if t in ('NI', 'NAO IDENTIFICADO') or '/' in t:
        return 'OUTROS'
    return 'CUSTEIO'


def mes_num(m):
    m = str(m).strip().lower()[:3]
    return MESES.index(m) + 1 if m in MESES else int(m)


def limpar(serie):
    """Remove pontos de carga incompleta: valor abaixo de 35% da mediana dos vizinhos."""
    out = list(serie)
    for i, v in enumerate(serie):
        if v is None:
            continue
        lo = max(0, i - 3)
        viz = [x for j, x in enumerate(serie[lo:i + 4]) if x is not None and lo + j != i]
        if len(viz) >= 2:
            med = statistics.median(viz)
            if med >= 50 and v < 0.35 * med:
                out[i] = None
    return out


def preencher(serie):
    n = len(serie); out = list(serie)
    for i, v in enumerate(serie):
        if v is None:
            p = next((serie[j] for j in range(i - 1, -1, -1) if serie[j] is not None), None)
            q = next((serie[j] for j in range(i + 1, n) if serie[j] is not None), None)
            vals = [x for x in (p, q) if x is not None]
            out[i] = sum(vals) / len(vals) if vals else 0
    return out


def montar(R):
    uf = R.get('uf', 'ES')
    ano_faf = int(R['fafAno'][0])
    ano_em = int(R['emAnoCorrente'])
    ente_faf = lambda mun, tp: EST if tp == 'ESTADUAL' else mun

    # ---------------- Repasses fundo a fundo do ano corrente ----------------
    entes = defaultdict(lambda: dict(fb=0, fl=0, pop=None, mes=[0] * 12, comp={}))
    for mun, tp, b, l, pop in R['fafTot']:
        e = entes[ente_faf(mun, tp)]; e['fb'] += b or 0; e['fl'] += l or 0
        if tp != 'ESTADUAL': e['pop'] = pop
    for mun, tp, mes, v in R['fafMes']:
        entes[ente_faf(mun, tp)]['mes'][mes_num(mes) - 1] += round(v or 0)
    comp_nomes = []
    for mun, tp, bloco, comp, v in R['fafComp']:
        if comp not in comp_nomes: comp_nomes.append(comp)
        k = (comp_nomes.index(comp), 1 if bloco.lower().startswith('estrut') else 0)
        c = entes[ente_faf(mun, tp)]['comp']; c[k] = c.get(k, 0) + round(v or 0)
    municipios = sorted(k for k in entes if k != EST)

    # ---------------- Saldos por ente, tipo de conta e data ----------------
    # por ente e data: total e por grupo
    por_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    ult = dt.date(1900, 1, 1)
    for mun, esf, tipo, dts, v in R['saldo']:
        d = dt.datetime.strptime(dts, '%d/%m/%Y').date(); ult = max(ult, d)
        e = EST if esf == 'ESTADUAL' else mun
        por_data[e][d][grupo(tipo)] += v or 0
    # meses de referência (desde jan/2014) com dado no painel
    meses = sorted({d.year * 100 + d.month for e in por_data for d in por_data[e] if d.year >= 2014})
    meses_all = sorted({d.year * 100 + d.month for e in por_data for d in por_data[e]})

    def mensal(e):
        """Por mês: escolhe a data com maior total (descarta cargas parciais do mesmo mês)."""
        best = {}
        for d, g in por_data[e].items():
            k = d.year * 100 + d.month; tot = sum(g.values())
            if k not in best or tot > best[k][0]: best[k] = (tot, g, d)
        return best

    saldo_ult = {}; serie = {}; mensal_g = {}
    for e in list(municipios) + [EST]:
        b = mensal(e); mensal_g[e] = b
        saldo_ult[e] = round(sum(por_data[e][ult].values()), 2) if ult in por_data[e] else 0
        serie[e] = limpar([round(b[m][0] / 1000) if m in b else None for m in meses])

    # ---------------- Repasses por tipo de conta (capacidade de execução) ----------------
    rep = defaultdict(lambda: defaultdict(float))       # (ente, yyyymm) -> grupo -> valor
    for mun, tp, tipo, ano, mes, v in R['repTipo']:
        rep[(ente_faf(mun, tp), int(ano) * 100 + mes_num(mes))][grupo(tipo)] += v or 0
    rep_tot = defaultdict(float)
    for mun, tp, ano, mes, v in R['repTot']:
        rep_tot[(ente_faf(mun, tp), int(ano) * 100 + mes_num(mes))] += v or 0

    # trimestres com saldo inicial e final disponíveis (fim de trimestre: mar, jun, set, dez)
    fim_tri = [m for m in meses_all if m % 100 in (3, 6, 9, 12)]
    ult_mes = ult.year * 100 + ult.month
    tri = []  # (rotulo, mes_inicial_saldo, meses_do_periodo, mes_final_saldo, parcial)
    for m in fim_tri:
        ano, mm = divmod(m, 100)
        ant = (ano - 1) * 100 + 12 if mm == 3 else ano * 100 + mm - 3
        if ant in meses_all and ano >= 2014:
            per = [ano * 100 + mm - 2, ano * 100 + mm - 1, m]
            tri.append((f'{(mm - 1) // 3 + 1}T{ano}', ant, per, m, False))
    if ult_mes % 100 not in (3, 6, 9, 12):
        ano, mm = divmod(ult_mes, 100); q = (mm - 1) // 3 + 1; ini = ano * 100 + (q - 1) * 3
        if q == 1: ini = (ano - 1) * 100 + 12
        if ini in meses_all:
            per = [ano * 100 + x for x in range((q - 1) * 3 + 1, mm + 1)]
            tri.append((f'{q}T{ano}*', ini, per, ult_mes, True))

    def trimestral(e):
        b = mensal_g[e]; out = {g: [] for g in GRUPOS}; out['TOTAL'] = []
        tot_ok = serie[e]
        idx = {m: i for i, m in enumerate(meses)}
        for rot, ini, per, fim, parc in tri:
            valido = ini in b and fim in b and (fim not in idx or tot_ok[idx[fim]] is not None) and (ini not in idx or tot_ok[idx[ini]] is not None)
            for g in GRUPOS + ['TOTAL']:
                if not valido:
                    out[g].append(None); continue
                si = b[ini][1] if g == 'TOTAL' else {g: b[ini][1].get(g, 0)}
                sf = b[fim][1] if g == 'TOTAL' else {g: b[fim][1].get(g, 0)}
                si = sum(si.values()); sf = sum(sf.values())
                en = sum(sum(rep[(e, m)].values()) if g == 'TOTAL' else rep[(e, m)].get(g, 0) for m in per)
                out[g].append([round(si / 1000), round(en / 1000), round(sf / 1000)])
        return {g: v for g, v in out.items() if any(x and (x[0] or x[1] or x[2]) for x in v)}

    # ---------------- Emendas ----------------
    ente_em = lambda esf, mun: EST if esf == 'ESTADUAL' else mun
    ano_d = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for esf, mun, ano, p, e, g in R['emAno']:
        a = ano_d[ente_em(esf, mun)][int(ano)]; a[0] += p or 0; a[1] += e or 0; a[2] += g or 0
    parl_nomes, ent_nomes, tipo_nomes = [], [], []
    ix = lambda lst, v: lst.index(v) if v in lst else (lst.append(v) or len(lst) - 1)
    parl_d = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for esf, mun, nome, p, g in R['emParl']:
        a = parl_d[ente_em(esf, mun)][ix(parl_nomes, nome)]; a[0] += p or 0; a[1] += g or 0
    prop_d = defaultdict(list)
    for esf, mun, pid, ent, tipo, p, e, g, aut in R['emProp']:
        auts = [ix(parl_nomes, a.strip()) for a in (aut or '').split(';') if a.strip()]
        prop_d[ente_em(esf, mun)].append([pid, ix(ent_nomes, ent), ix(tipo_nomes, tipo), round(p or 0), round(e or 0), round(g or 0), auts])

    oficiais, acc = nomes_oficiais(uf)

    def bloco(e, nome):
        f = entes[e]
        fe = sum(v for (ci, b), v in f['comp'].items() if b == 1)
        return dict(n=nome, nm=oficiais.get(sem_acento(nome), '') if e != EST else '', pop=f['pop'], fb=round(f['fb'], 2), fl=round(f['fl'], 2), fe=fe, fm=round(f['fb'] - fe, 2),
                    mes=f['mes'], comp=[[ci, b, v] for (ci, b), v in f['comp'].items()],
                    s=saldo_ult.get(e, 0), sal=serie[e], tri=trimestral(e),
                    ano=sorted([[y] + [round(x) for x in v] for y, v in ano_d[e].items()]),
                    parl=sorted([[k] + [round(x) for x in v] for k, v in parl_d[e].items()], key=lambda x: -x[1]),
                    prop=sorted(prop_d[e], key=lambda x: -(x[3] - x[5])))

    D = dict(meta=dict(extracao=dt.datetime.fromisoformat(R['extraidoEm'].replace('Z', '+00:00')).astimezone(dt.timezone(dt.timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'),
                       saldoData=ult.strftime('%d/%m/%Y'), anoFaf=ano_faf, anoEm=ano_em, fns=R.get('apps', {}), uf=uf),
             acc=acc, months=meses, comp=comp_nomes, parl=parl_nomes, ent=ent_nomes, tipo=tipo_nomes, grupos=GRUPOS,
             tri=[t[0] for t in tri],
             m=[bloco(mn, mn) for mn in municipios], EST=bloco(EST, 'GOVERNO DO ESTADO'))
    # série total do ES (preenchendo pontos removidos de cada ente)
    tot = [0] * len(meses)
    for e in municipios + [EST]:
        tot = [a + b for a, b in zip(tot, preencher(serie[e]))]
    D['esSal'] = [round(x) for x in tot]
    return D


def validar(D):
    """Checagens mínimas antes de publicar. Lança erro se algo estiver fora do esperado."""
    erros = []
    uf = D['meta'].get('uf', 'ES'); esp = ESPERADOS.get(uf)
    # tolera até 1% de municípios sem repasse no ano (nunca mais do que o total do IBGE)
    if esp and not (esp * 0.99 <= len(D['m']) <= esp):
        erros.append(f"{uf}: esperados {esp} municípios, vieram {len(D['m'])}")
    elif esp and len(D['m']) != esp:
        print(f"aviso: {uf} com {len(D['m'])} de {esp} municípios no fundo a fundo")
    fb = sum(m['fb'] for m in D['m']) + D['EST']['fb']
    if fb <= 0: erros.append('repasse fundo a fundo zerado')
    s = sum(m['s'] for m in D['m']) + D['EST']['s']
    if s <= 0: erros.append('saldo total zerado')
    ep = sum(sum(a[1] for a in m['ano'] if a[0] == D['meta']['anoEm']) for m in D['m'] + [D['EST']])
    if ep <= 0: erros.append('emendas do ano corrente zeradas')
    import datetime
    hoje = datetime.date.today().year
    if not (hoje - 1 <= D['meta']['anoFaf'] <= hoje): erros.append(f"ano do fundo a fundo fora do esperado: {D['meta']['anoFaf']}")
    if erros: raise SystemExit('VALIDAÇÃO FALHOU: ' + '; '.join(erros))
    return dict(uf=uf, municipios=len(D['m']), faf=round(fb), saldo=round(s), emendas=round(ep))


def comparar(n, a):
    """Trava de segurança: recusa publicar se o dado novo variar demais em relação ao publicado."""
    if not a.get('m') or a.get('meta', {}).get('uf', 'ES') != n['meta'].get('uf', 'ES'):
        return
    tot = lambda d: sum(m['s'] for m in d['m']) + d['EST']['s']
    fb = lambda d: sum(m['fb'] for m in d['m']) + d['EST']['fb']
    tn, ta = tot(n), tot(a)
    if n['meta']['anoFaf'] == a['meta']['anoFaf'] and fb(a) and not 0.6 < fb(n) / fb(a) < 1.5:
        raise SystemExit(f"variação suspeita do fundo a fundo: {fb(a):.0f} -> {fb(n):.0f}; publicação suspensa")
    if ta and abs(tn / ta - 1) > 0.4:
        raise SystemExit(f'variação suspeita do saldo total: {ta:.0f} -> {tn:.0f}; publicação suspensa')
    print(f'saldo total: {ta:.0f} -> {tn:.0f}')


if __name__ == '__main__':
    args = sys.argv[1:]
    anterior = None
    if '--anterior' in args:
        i = args.index('--anterior'); anterior = args[i + 1]; del args[i:i + 2]
    R = json.load(open(args[0], encoding='utf-8'))
    D = montar(R)
    print('conferência:', validar(D))
    if anterior and pathlib.Path(anterior).exists():
        comparar(D, json.load(open(anterior, encoding='utf-8')))
    json.dump(D, open(args[1], 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
