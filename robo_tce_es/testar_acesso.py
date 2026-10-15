#!/usr/bin/env python3
"""
Teste de acesso ao Painel de Controle do TCE-ES (paineldecontrole.tcees.tc.br).

O painel de "Gastos com a funcao saude" (e os demais paineis tematicos do site)
sao relatorios Power BI "publicar na web", incorporados via iframe
app.powerbi.com/view?r=<token>&pageName=<pagina>. Nao existe API REST aberta
do proprio TCE-ES: os dados reais chegam por uma chamada interna do Power BI
(normalmente para *.analysis.windows.net, endpoint "querydata" ou similar).

Este script NAO extrai dados ainda. Ele so testa se, a partir deste ambiente,
e possivel:
  1. alcancar app.powerbi.com (sem bloqueio de rede/IP);
  2. o relatorio carregar e disparar a chamada interna de dados;
  3. capturar essa resposta para depois desenhar o parser definitivo.

Uso: python testar_acesso.py [saida.json]
Saida: grava um resumo em saida.json (padrao: resultado_teste.json) e imprime
no console um resumo legivel (para aparecer no log do GitHub Actions).
"""
import asyncio
import json
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# Relatorio "Saude" do Painel de Controle do TCE-ES.
# k = chave publica do relatorio; t = tenant; pageName = pagina "Gastos com a funcao saude".
# As demais paginas do mesmo painel de saude (Estabelecimentos, Leitos, Equipamentos,
# Planos Municipais, Detalhamento dos planos) usam o MESMO k/t, trocando so o pageName.
REPORT_KEY = "0b4992ae-e680-4f0c-b307-83c889f69479"
TENANT = "9d1437b1-472c-4501-9439-dcfe9a41f2b0"
PAGE_NAME = "ReportSection544931c3083d7668ba47"  # Gastos com a funcao saude

import base64

def build_url() -> str:
    token = json.dumps({"k": REPORT_KEY, "t": TENANT})
    r = base64.b64encode(token.encode()).decode()
    return f"https://app.powerbi.com/view?r={r}&pageName={PAGE_NAME}"


async def main(out_path: str) -> int:
    url = build_url()
    capturados = []
    erros = []

    async def on_response(resp):
        u = resp.url
        host = u.split("/")[2] if "//" in u else ""
        interessante = (
            "analysis.windows.net" in host
            or "powerbi.com" in host
            and any(p in u.lower() for p in ["query", "models", "schema", "explor"])
        )
        if interessante:
            item = {"url": u, "status": resp.status, "frame": resp.frame.url if resp.frame else None}
            # O Power BI as vezes declara "text/plain" num corpo que na verdade e JSON
            # (resposta do endpoint "querydata"), entao sempre tentamos ler o corpo
            # das chamadas de dados em vez de confiar so no content-type.
            eh_querydata = "querydata" in u.lower()
            ct = resp.headers.get("content-type", "")
            if "json" in ct or eh_querydata:
                try:
                    body = await resp.body()
                    item["tamanho_bytes"] = len(body)
                    item["content_type"] = ct
                    texto = body.decode("utf-8", errors="replace")
                    item["trecho"] = texto[:500]
                    if eh_querydata:
                        # guarda a resposta completa das chamadas de querydata num
                        # arquivo separado (pode ser grande) para analise do formato
                        idx = sum(1 for c in capturados if "querydata" in c["url"].lower())
                        with open(f"querydata_{idx}.json", "w", encoding="utf-8") as fq:
                            fq.write(texto)
                except Exception as e:  # noqa: BLE001
                    item["erro_leitura"] = str(e)[:200]
            else:
                item["content_type"] = ct
            capturados.append(item)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        status_navegacao = None
        try:
            resp = await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            status_navegacao = resp.status if resp else None
        except Exception as e:  # noqa: BLE001
            erros.append(f"erro no goto: {e}")

        # da tempo do iframe interno do Power BI carregar e disparar as chamadas de dados
        await page.wait_for_timeout(20000)

        try:
            await page.screenshot(path="captura_teste.png", full_page=False)
        except Exception as e:  # noqa: BLE001
            erros.append(f"erro no screenshot: {e}")

        await browser.close()

    resultado = {
        "quando_utc": datetime.now(timezone.utc).isoformat(),
        "url_testada": url,
        "status_navegacao": status_navegacao,
        "qtd_chamadas_relevantes_capturadas": len(capturados),
        "chamadas": capturados[:10],
        "erros": erros,
        "veredito": "ACESSO_OK_COM_DADOS" if capturados else "SEM_CHAMADA_DE_DADOS_CAPTURADA",
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Teste de acesso ao Painel de Controle TCE-ES (Power BI) ===")
    print(f"URL testada: {url}")
    print(f"HTTP da navegacao inicial: {status_navegacao}")
    print(f"Chamadas de dados relevantes capturadas: {len(capturados)}")
    for c in capturados[:5]:
        print(f"  - {c.get('status')} {c['url'][:140]}")
    if erros:
        print("Erros:")
        for e in erros:
            print(f"  - {e}")
    print(f"VEREDITO: {resultado['veredito']}")

    return 0 if capturados else 1


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "resultado_teste.json"
    rc = asyncio.run(main(saida))
    sys.exit(rc)
