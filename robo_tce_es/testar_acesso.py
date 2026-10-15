#!/usr/bin/env python3
"""
Teste de acesso ao Painel de Controle do TCE-ES (paineldecontrole.tcees.tc.br).

O painel de "Gastos com a funcao saude" (e os demais paineis tematicos do site)
sao relatorios Power BI "publicar na web", incorporados via iframe
app.powerbi.com/view?r=<token>&pageName=<pagina>. Nao existe API REST aberta
do proprio TCE-ES: os dados reais chegam por uma chamada interna do Power BI
para *.analysis.windows.net, endpoint "querydata".

Este script captura TODAS as chamadas querydata (requisicao + resposta) feitas
ao carregar a pagina "Gastos com a funcao saude", para dar base ao parser
definitivo (extrair.py) e para testar se o corpo da requisicao pode ser
reenviado depois via HTTP puro (sem precisar abrir navegador toda vez).

Uso: python testar_acesso.py [saida.json]
Saida: grava um resumo em saida.json (padrao: resultado_teste.json) e imprime
no console um resumo legivel (para aparecer no log do GitHub Actions).
"""
import asyncio
import base64
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


def build_url() -> str:
    token = json.dumps({"k": REPORT_KEY, "t": TENANT})
    r = base64.b64encode(token.encode()).decode()
    return f"https://app.powerbi.com/view?r={r}&pageName={PAGE_NAME}"


async def main(out_path: str) -> int:
    url = build_url()
    # chave = requestId da chamada querydata (correlaciona pedido <-> resposta)
    pedidos: dict[str, dict] = {}
    respostas: dict[str, dict] = {}
    outras_chamadas = []
    erros = []

    async def on_request(req):
        if "querydata" in req.url.lower():
            pedidos[id(req)] = {
                "url": req.url,
                "method": req.method,
                "headers": dict(req.headers),
                "post_data": req.post_data,
            }
            # guarda a correlacao por objeto de requisicao para casar com a resposta
            req._chave_captura = id(req)  # type: ignore[attr-defined]

    async def on_response(resp):
        u = resp.url
        host = u.split("/")[2] if "//" in u else ""
        eh_querydata = "querydata" in u.lower()
        relevante_mas_nao_querydata = (
            not eh_querydata
            and (
                "analysis.windows.net" in host
                or ("powerbi.com" in host and any(p in u.lower() for p in ["models", "schema", "explor"]))
            )
        )
        if eh_querydata:
            try:
                body = await resp.body()
                texto = body.decode("utf-8", errors="replace")
                chave_req = getattr(resp.request, "_chave_captura", None)
                respostas[len(respostas)] = {
                    "url": u,
                    "status": resp.status,
                    "content_type": resp.headers.get("content-type", ""),
                    "tamanho_bytes": len(body),
                    "corpo_completo": texto,
                    "pedido": pedidos.get(chave_req),
                }
            except Exception as e:  # noqa: BLE001
                erros.append(f"erro lendo resposta querydata ({u[:80]}): {e}")
        elif relevante_mas_nao_querydata:
            ct = resp.headers.get("content-type", "")
            item = {"url": u, "status": resp.status, "content_type": ct}
            outras_chamadas.append(item)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 2400})
        page.on("request", lambda r: asyncio.create_task(on_request(r)))
        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        status_navegacao = None
        try:
            resp = await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            status_navegacao = resp.status if resp else None
        except Exception as e:  # noqa: BLE001
            erros.append(f"erro no goto: {e}")

        # da tempo do iframe interno do Power BI carregar e disparar as chamadas de dados
        await page.wait_for_timeout(15000)

        # forca o carregamento de visuais que soh renderizam quando entram na tela
        # (scroll dentro do iframe do relatorio), repetindo a espera entre rolagens
        try:
            frame = next((f for f in page.frames if "powerbi.com" in f.url), None)
            if frame:
                for _ in range(6):
                    await frame.evaluate("window.scrollBy(0, 600)")
                    await page.wait_for_timeout(1500)
        except Exception as e:  # noqa: BLE001
            erros.append(f"erro ao rolar o relatorio: {e}")

        await page.wait_for_timeout(8000)

        try:
            await page.screenshot(path="captura_teste.png", full_page=False)
        except Exception as e:  # noqa: BLE001
            erros.append(f"erro no screenshot: {e}")

        await browser.close()

    lista_querydata = list(respostas.values())
    resultado = {
        "quando_utc": datetime.now(timezone.utc).isoformat(),
        "url_testada": url,
        "status_navegacao": status_navegacao,
        "qtd_querydata_capturadas": len(lista_querydata),
        "qtd_outras_chamadas_relevantes": len(outras_chamadas),
        "querydata": lista_querydata,
        "outras_chamadas": outras_chamadas[:15],
        "erros": erros,
        "veredito": "ACESSO_OK_COM_DADOS" if lista_querydata else "SEM_CHAMADA_DE_DADOS_CAPTURADA",
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("=== Teste de acesso ao Painel de Controle TCE-ES (Power BI) ===")
    print(f"URL testada: {url}")
    print(f"HTTP da navegacao inicial: {status_navegacao}")
    print(f"Chamadas querydata capturadas: {len(lista_querydata)}")
    for c in lista_querydata:
        tem_pedido = "com pedido" if c.get("pedido") else "SEM pedido correlacionado"
        print(f"  - status={c['status']} bytes={c['tamanho_bytes']} ({tem_pedido})")
    if erros:
        print("Erros:")
        for e in erros:
            print(f"  - {e}")
    print(f"VEREDITO: {resultado['veredito']}")

    return 0 if lista_querydata else 1


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "resultado_teste.json"
    rc = asyncio.run(main(saida))
    sys.exit(rc)
