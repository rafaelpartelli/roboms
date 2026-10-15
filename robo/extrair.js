// Extração dos Painéis InvestSUS (FNS) para o Radar de Recursos SUS ES.
// Executado dentro da página https://investsuspaineis.saude.gov.br/extensions/CGIN_InvestsusPaineis/CGIN_InvestsusPaineis.html
// Retorna (Promise) um objeto JSON com os dados brutos do Espírito Santo.
async function extrairInvestsus(UF) {
  UF = UF || 'ES';
  const APPS = {
    FAF: '8d8da3af-4b18-4305-9584-715ee15b4e40',     // Repasses Fundo a Fundo
    SAL: '2967afcf-2814-4110-9c80-bd81574c894e',     // Saldos de Repasses
    EME: '585aca8d-2714-487d-a08e-34150047e7dd'      // Emendas Parlamentares
  };
  const qlik = await new Promise(r => require(['js/qlik'], r));
  const cfg = { host: location.hostname, prefix: '/', port: location.port, isSecure: true };
  const A = {}; for (const k in APPS) A[k] = qlik.openApp(APPS[k], cfg);

  async function pull(app, dims, meas) {
    const nc = dims.length + meas.length;
    const m = await app.createCube({
      qDimensions: dims.map(d => ({ qDef: { qFieldDefs: [d] }, qNullSuppression: true })),
      qMeasures: meas.map(x => ({ qDef: { qDef: x } })), qSuppressZero: true, qSuppressMissing: true,
      qInitialDataFetch: [{ qTop: 0, qLeft: 0, qWidth: nc, qHeight: 1 }]
    });
    const lay = await m.enigmaModel.getLayout();
    const tot = lay.qHyperCube.qSize.qcy, h = Math.floor(9000 / nc), out = [];
    for (let t = 0; t < tot; t += h) {
      const p = await m.enigmaModel.getHyperCubeData('/qHyperCubeDef', [{ qTop: t, qLeft: 0, qWidth: nc, qHeight: h }]);
      p[0].qMatrix.forEach(r => out.push(r.map((c, i) => i < dims.length ? c.qText :
        (c.qNum === 'NaN' || isNaN(c.qNum) ? (c.qText === '-' ? null : c.qText) : Math.round(c.qNum * 100) / 100))));
    }
    try { app.destroySessionObject(m.id); } catch (e) { }
    return out;
  }
  async function reload(app) {
    return new Promise(res => app.getAppLayout(l => res(l.qLastReloadTime || null)));
  }

  const R = { uf: UF, extraidoEm: new Date().toISOString(), apps: {} };
  for (const k in A) R.apps[k] = await reload(A[k]);
  const U = `UF={'${UF}'}`, UC = `UF_C={'${UF}'}`, UP = `SG_UF_PROPOSTA={'${UF}'}`;

  // 1. Repasses fundo a fundo (ano corrente do painel)
  R.fafAno = (await pull(A.FAF, ['ANO'], [`Sum({<${U}>} VL_BRUTO)`]))[0];
  R.fafTot = await pull(A.FAF, ['MUNICIPIO', 'TP_REPASSE'], [`Sum({<${U}>} VL_BRUTO)`, `Sum({<${U}>} VL_LIQUIDO)`, `Max({<${U}>} QT_POPULACAO)`]);
  R.fafMes = await pull(A.FAF, ['MUNICIPIO', 'TP_REPASSE', 'MES'], [`Sum({<${U}>} VL_BRUTO)`]);
  R.fafComp = await pull(A.FAF, ['MUNICIPIO', 'TP_REPASSE', 'BLOCO', 'COMPONENTE'], [`Sum({<${U}>} VL_BRUTO)`]);

  // 2. Saldos em conta por ente, esfera, tipo de conta e data (desde 2013)
  R.saldo = await pull(A.SAL, ['MUN_C', 'ESFERA_C', 'TIPO_C', 'DT_SALDO'],
    [`Sum({<${UC},DT_SALDO={"=Year(DT_SALDO)>=2013"}>} VL_TOTAL_SALDO)`]);
  // 3. Repasses por ente, tipo de conta de destino e mês (desde 2013), para a capacidade de execução
  R.repTipo = await pull(A.SAL, ['MUNICIPIO', 'TP_REPASSE', 'TIPO_C', 'ANO', 'MES'], [`Sum({<${U},ANO={">=2013"}>} VL_LIQUIDO)`]);
  R.repTot = await pull(A.SAL, ['MUNICIPIO', 'TP_REPASSE', 'ANO', 'MES'], [`Sum({<${U},ANO={">=2013"}>} VL_LIQUIDO)`]);

  // 4. Emendas parlamentares (esfera E = estadual; demais = município)
  const anoEm = Math.max(...(await pull(A.EME, ['NU_ANO'], [`Sum({<${UP}>} VL_TOTAL_PROPOSTA)`])).map(r => +r[0]));
  R.emAnoCorrente = anoEm;
  R.emAno = await pull(A.EME, ['CO_ESFERA_ADMINISTRATIVA_TA', 'NO_MUNICIPIO', 'NU_ANO'],
    [`Sum({<${UP}>} VL_TOTAL_PROPOSTA)`, `Sum({<${UP}>} VL_EMPENHADO)`, `Sum({<${UP}>} VL_PAGO)`]);
  const F = `${UP},NU_ANO={${anoEm}}`;
  R.emParl = await pull(A.EME, ['CO_ESFERA_ADMINISTRATIVA_TA', 'NO_MUNICIPIO', 'NO_PARLAMENTAR'],
    [`Sum({<${F}>} VL_TOTAL_PROPOSTA)`, `Sum({<${F}>} VL_PAGO)`]);
  R.emProp = await pull(A.EME, ['CO_ESFERA_ADMINISTRATIVA_TA', 'NO_MUNICIPIO', 'NU_PROPOSTA', 'NOME_ENTIDADE_TA', 'DS_TIPO_PROPOSTA'],
    [`Sum({<${F}>} VL_TOTAL_PROPOSTA)`, `Sum({<${F}>} VL_EMPENHADO)`, `Sum({<${F}>} VL_PAGO)`, `Concat(distinct {<${F}>} NO_PARLAMENTAR,'; ')`]);
  return R;
}
