#!/usr/bin/env python3
"""Robô DOU: baixa o Diário Oficial da União (INLABS, Imprensa Nacional),
filtra portarias do Ministério da Saúde e gera CSV (e e-mail opcional).

Credenciais SOMENTE por variáveis de ambiente:
  INLABS_EMAIL, INLABS_SENHA
Opcional (e-mail): SMTP_USER, SMTP_PASS (senha de app), MAIL_TO
Uso:
  python3 robo_dou.py                 # hoje
  python3 robo_dou.py --days 7        # últimos 7 dias
  python3 robo_dou.py --date 2026-09-30 --email
  python3 robo_dou.py --radar-csv     # refaz o radar.json a partir dos CSV ja salvos (sem acessar o INLABS)

A cada execucao tambem atualiza saida/radar.json, lido pela pagina Radar Saude do site.
"""
import argparse, csv, io, json, os, re, smtplib, sys, zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo
import requests

BASE = "https://inlabs.in.gov.br"
SECOES = ["DO1", "DO1E"]            # Seção 1 e edições extras
ORGAO = "ministério da saúde"        # filtro em artCategory
TIPO = "portaria"                    # filtro em artType
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida")


def login():
    s = requests.Session()
    email, senha = os.environ.get("INLABS_EMAIL"), os.environ.get("INLABS_SENHA")
    if not email or not senha:
        sys.exit("Defina INLABS_EMAIL e INLABS_SENHA no ambiente.")
    s.post(f"{BASE}/logar.php", data={"email": email, "password": senha}, timeout=60)
    if not s.cookies.get("inlabs_session_cookie"):
        sys.exit("Login falhou: confira e-mail/senha do INLABS.")
    return s


def baixar(s, dia, secao):
    nome = f"{dia:%Y-%m-%d}-{secao}.zip"
    r = s.get(f"{BASE}/index.php", params={"p": f"{dia:%Y-%m-%d}", "dl": nome}, timeout=120)
    ok = r.status_code == 200 and r.content[:2] == b"PK"
    return r.content if ok else None


def texto(el, tag):
    x = el.find(f".//{tag}")
    return re.sub(r"<[^>]+>|\s+", " ", "".join(x.itertext())).strip() if x is not None else ""


def extrair(zbytes, dia, secao):
    achados = []
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for n in z.namelist():
            if not n.lower().endswith(".xml"):
                continue
            try:
                root = ET.fromstring(z.read(n))
            except ET.ParseError:
                continue
            for a in root.iter("article"):
                cat, tipo = a.get("artCategory", ""), a.get("artType", "")
                if ORGAO in cat.lower() and TIPO in tipo.lower():
                    achados.append({
                        "data": f"{dia:%d/%m/%Y}", "secao": secao,
                        "tipo": tipo, "orgao": cat,
                        "titulo": texto(a, "Identifica") or a.get("name", ""),
                        "ementa": texto(a, "Ementa"),
                        "link": a.get("pdfPage", ""),
                    })
    return achados


TEMAS = [
    ("Habilitações e qualificações", r"habilita|qualifica|renova"),
    ("Tabela SUS e procedimentos", r"tabela de procedimentos|sigtap|procedimento"),
    ("Programas e políticas", r"agora tem especialistas|melhor em casa|programa|política"),
    ("Financiamento e incentivos", r"incentivo|recurso|repasse|financeir|transfer|custeio|emenda|piso|r\$"),
    ("Normas e regulamentos", r"consolida|regulament|institui|dispõe|dispoe|diretriz|protocolo|altera"),
    ("Gestão administrativa", r"fun[cç][aãoõ]|cargo|comiss|designa|nomeia|estrutura|regimento"),
]
IMPACTO = [(r"suspens", 3), (r"r\$", 3), (r"incentivo|piso|emenda", 2), (r"institui|altera|revoga|prorroga", 1)]


def tema_de(it):
    t = f"{it['titulo']} {it['ementa']}".lower()
    for nome, rx in TEMAS:
        if re.search(rx, t):
            return nome
    return "Outros"


def pontos(it):
    t = f"{it['titulo']} {it['ementa']}".lower()
    if re.search(r"renova qualifica", t):
        return 0
    return sum(p for rx, p in IMPACTO if re.search(rx, t))


def esc(x):
    return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def montar_html(itens, periodo, ref):
    AZ, AZ2, VD, FD, LN = "#0C326F", "#1351B4", "#168821", "#F3F6FB", "#D5DDEA"
    total = len(itens)
    por = {}
    for it in itens:
        por.setdefault(tema_de(it), []).append(it)
    ordem = sorted(por, key=lambda k: -len(por[k]))
    h = [f'<div style="background:#F2F4F7;padding:16px 0;font-family:Arial,Helvetica,sans-serif;color:#1F2933">'
         f'<table role="presentation" width="100%" style="max-width:640px;margin:0 auto;background:#fff;border-collapse:collapse">'
         f'<tr><td style="background:{AZ};padding:22px 24px;color:#fff">'
         f'<div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#BFD0EE">Relatório executivo diário</div>'
         f'<div style="font-size:24px;font-weight:bold;margin:4px 0">Portarias do Ministério da Saúde</div>'
         f'<div style="font-size:14px;color:#D9E4F7">DOU de {esc(ref)} | {total} portaria(s) | Fonte: INLABS, Imprensa Nacional</div></td></tr>']
    if total == 0:
        h.append(f'<tr><td style="padding:24px;font-size:15px">Nenhuma portaria do Ministério da Saúde foi encontrada no período ({esc(periodo)}).</td></tr>')
    else:
        lider = ordem[0]
        pl = 100 * len(por[lider]) / total
        h.append(f'<tr><td style="padding:20px 24px"><div style="font-size:20px;font-weight:bold;color:{AZ}">Em síntese</div>'
                 f'<div style="background:{FD};border-left:4px solid {VD};padding:12px 14px;margin-top:8px;font-size:15px;line-height:1.5">'
                 f'Foram publicadas <b>{total} portaria(s)</b> do Ministério da Saúde. O tema com maior volume foi '
                 f'<b>{esc(lider)}</b>, com {len(por[lider])} ato(s) (<b>{pl:.1f}%</b> do total).</div></td></tr>')
        h.append(f'<tr><td style="padding:0 24px 8px"><div style="font-size:20px;font-weight:bold;color:{AZ};margin-bottom:8px">Painel por tema</div>'
                 f'<table role="presentation" width="100%" style="border-collapse:collapse;font-size:14px">')
        for k in ordem:
            pc = 100 * len(por[k]) / total
            h.append(f'<tr><td style="padding:6px 0;width:48%">{esc(k)}</td>'
                     f'<td style="padding:6px 0"><table role="presentation" width="100%" style="border-collapse:collapse"><tr>'
                     f'<td style="background:{AZ2};height:12px;width:{max(pc,3):.0f}%"></td><td style="background:{FD}"></td></tr></table></td>'
                     f'<td style="padding:6px 0 6px 8px;width:20%;text-align:right;white-space:nowrap"><b>{len(por[k])}</b> ({pc:.1f}%)</td></tr>')
        h.append('</table></td></tr>')
        dest = sorted([i for i in itens if pontos(i) > 0], key=lambda i: -pontos(i))[:5]
        h.append(f'<tr><td style="padding:12px 24px"><div style="font-size:20px;font-weight:bold;color:{AZ};margin-bottom:8px">Portarias de maior atenção</div>')
        if dest:
            for i in dest:
                lk = (f'<a href="{esc(i["link"])}" style="color:{AZ2}">Abrir no DOU</a>' if i["link"] else "Fonte: DOU")
                h.append(f'<div style="border:1px solid {LN};border-top:4px solid {AZ2};border-radius:10px;padding:12px 14px;margin-bottom:10px">'
                         f'<div style="font-size:15px;font-weight:bold;color:{AZ}">{esc(i["titulo"])}</div>'
                         f'<div style="font-size:14px;line-height:1.5;margin:6px 0">{esc(i["ementa"])}</div>'
                         f'<div style="font-size:13px">{lk}</div></div>')
        else:
            h.append('<div style="font-size:14px;color:#4B5563">Nenhuma portaria com sinal de impacto direto nas ementas (valores, suspensão ou mudança de regra). Atos de rotina listados abaixo.</div>')
        h.append('</td></tr>')
        h.append(f'<tr><td style="padding:12px 24px"><div style="font-size:20px;font-weight:bold;color:{AZ};margin-bottom:8px">Todas as portarias do dia</div>')
        for k in ordem:
            h.append(f'<div style="font-size:15px;font-weight:bold;color:{VD};margin:12px 0 4px">{esc(k)} ({len(por[k])})</div>'
                     f'<table role="presentation" width="100%" style="border-collapse:collapse;font-size:13px">'
                     f'<tr><td style="background:{AZ};color:#fff;padding:6px 8px;width:30%"><b>Portaria</b></td>'
                     f'<td style="background:{AZ};color:#fff;padding:6px 8px"><b>Assunto</b></td></tr>')
            for n, i in enumerate(por[k]):
                bg = FD if n % 2 else "#fff"
                lk = (f'<a href="{esc(i["link"])}" style="color:{AZ2}">{esc(i["titulo"])}</a>' if i["link"] else esc(i["titulo"]))
                h.append(f'<tr><td style="background:{bg};padding:6px 8px;border-bottom:1px solid {LN};vertical-align:top">{lk}</td>'
                         f'<td style="background:{bg};padding:6px 8px;border-bottom:1px solid {LN};vertical-align:top">{esc(i["ementa"])}</td></tr>')
            h.append('</table>')
        h.append('</td></tr>')
    h.append(f'<tr><td style="background:#08234F;color:#C9D6EE;padding:16px 24px;font-size:12px;line-height:1.5">'
             f'Relatório gerado automaticamente a partir do DOU (INLABS). Temas atribuídos por palavras-chave das ementas; '
             f'o texto integral publicado no DOU prevalece. Análise ampliada com riscos e metas segue no Radar Diário.</td></tr></table></div>')
    return "".join(h)


def enviar_email(arquivo, itens, periodo, ref, anexar_csv=False):
    """E-mail em formato de relatório executivo (HTML). A parte em texto simples mantém
    o formato [ROBO-DOU] lido pela atividade agendada do Claude. Sempre enviado, mesmo com 0 portarias."""
    msg = EmailMessage()
    msg["Subject"] = f"[ROBO-DOU] Portarias MS | {ref} | {len(itens)} portarias"
    msg["From"], msg["To"] = os.environ["SMTP_USER"], os.environ["MAIL_TO"]
    linhas = [f"ROBO-DOU | Ministerio da Saude | Periodo: {periodo} | Total: {len(itens)}", ""]
    for i, it in enumerate(itens, 1):
        linhas += [f"#{i} | {it['data']} | {it['secao']} | {it['tipo']}",
                   f"TITULO: {it['titulo']}",
                   f"EMENTA: {it['ementa']}",
                   f"LINK: {it['link']}", ""]
    if not itens:
        linhas.append("Nenhuma portaria do Ministerio da Saude encontrada no periodo.")
    msg.set_content("\n".join(linhas))
    msg.add_alternative(montar_html(itens, periodo, ref), subtype="html")
    if anexar_csv:
        with open(arquivo, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="csv", filename=os.path.basename(arquivo))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as srv:
        srv.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        srv.send_message(msg)


RADAR_MAX = 80


def _limpa_titulo(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    t = re.sub(r"\bDE\b", "de", t)
    t = re.sub(r"\b(JANEIRO|FEVEREIRO|MAR\u00c7O|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)\b", lambda m: m.group(1).lower(), t)
    return re.sub(r"^PORTARIA\b", "Portaria", t)


def _item_radar(it):
    ementa = re.sub(r"\s*Ref\.:.*$", "", it.get("ementa") or "").strip()
    orgao = it["orgao"].split("/")[-1].strip() if it.get("orgao") else ""
    return {
        "data": datetime.strptime(it["data"], "%d/%m/%Y").strftime("%Y-%m-%d"),
        "tipo": "Portaria", "numero": "", "orgao": orgao, "tema": tema_de(it),
        "titulo": _limpa_titulo(it["titulo"]),
        "resumo": ementa or "Ementa n\u00e3o publicada no extrato do DOU. Consulte o texto oficial.",
        "url": (it.get("link") or "").replace("http://", "https://", 1),
        "_p": pontos(it),
    }


def atualizar_radar(itens, destino=None):
    """Mantem saida/radar.json (lido pelo site). Faz mescla com o arquivo anterior,
    remove duplicados, ordena por data e relevancia e guarda os RADAR_MAX mais recentes.
    Itens sem link oficial nao entram. As chaves nacional e es sao preservadas."""
    destino = destino or os.path.join(OUT, "radar.json")
    atual = {}
    for caminho in (destino, os.environ.get("RADAR_BASE")):
        if caminho and os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                atual = json.load(f)
            break
    novos = [_item_radar(i) for i in itens if i.get("link")]
    vistos, junto = set(), []
    for p in novos + atual.get("portarias", []):
        k = (p["url"], p["titulo"])
        if k not in vistos:
            vistos.add(k)
            junto.append(p)
    junto.sort(key=lambda p: (p["data"], p.get("_p", 0)), reverse=True)
    for p in junto:
        p.pop("_p", None)
    saida = {
        "atualizado": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d"),
        "portarias": junto[:RADAR_MAX],
        "nacional": atual.get("nacional", []),
        "es": atual.get("es", []),
    }
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    os.replace(tmp, destino)
    return destino, len(saida["portarias"])


def ler_csvs():
    itens = []
    for nome in sorted(os.listdir(OUT)):
        if nome.startswith("portarias_ms_") and nome.endswith(".csv"):
            with open(os.path.join(OUT, nome), encoding="utf-8-sig", newline="") as f:
                itens += list(csv.DictReader(f, delimiter=";"))
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--email", action="store_true")
    ap.add_argument("--anexar-csv", action="store_true")
    ap.add_argument("--radar-csv", action="store_true")
    a = ap.parse_args()
    if a.radar_csv:
        arq, n = atualizar_radar(ler_csvs())
        print(f"Radar: {n} portarias em {arq}")
        return
    fim = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    dias = [fim - timedelta(days=i) for i in range(a.days)][::-1]
    s, todos = login(), []
    for d in dias:
        for sec in SECOES:
            z = baixar(s, d, sec)
            if z:
                novos = extrair(z, d, sec); todos += novos
                print(f"{d} {sec}: {len(novos)} portarias")
            else:
                print(f"{d} {sec}: sem arquivo")
    os.makedirs(OUT, exist_ok=True)
    per = f"{dias[0]:%Y%m%d}_{dias[-1]:%Y%m%d}"
    arq = os.path.join(OUT, f"portarias_ms_{per}.csv")
    with open(arq, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["data", "secao", "tipo", "orgao", "titulo", "ementa", "link"], delimiter=";")
        w.writeheader(); w.writerows(todos)
    print(f"Total: {len(todos)} | arquivo: {arq}")
    try:
        rj, n = atualizar_radar(todos)
        print(f"Radar: {n} portarias em {rj}")
    except Exception as e:  # nao impede o envio do e-mail
        print(f"Radar JSON falhou: {e}")
    if a.email:
        enviar_email(arq, todos, f"{dias[0]:%d/%m} a {dias[-1]:%d/%m/%Y}", f"{dias[-1]:%d/%m/%Y}", a.anexar_csv)


if __name__ == "__main__":
    main()
