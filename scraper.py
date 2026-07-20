# scraper.py
"""
Lê links.txt, resolve links amzn.to, limpa o URL,
faz scraping e gera/actualiza produtos_novos.csv.
"""

import os
import re
import csv
import time
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

ASSOCIATE_TAG  = os.getenv("AMAZON_ASSOCIATE_TAG", "")
FICHEIRO_LINKS = "links.txt"
FICHEIRO_CSV   = "produtos_novos.csv"
CABECALHO      = [
    "titulo", "preco", "preco_anterior", "desconto",
    "imagem", "link",
    "caracteristica1", "caracteristica2", "caracteristica3"
]

HEADERS_LIST = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,pt;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]


def extrair_asin(url: str) -> str | None:
    """Extrai o ASIN de qualquer URL Amazon."""
    padrao = re.search(
        r"/(?:dp|gp/product|product)/([A-Z0-9]{10})",
        url, re.IGNORECASE
    )
    return padrao.group(1).upper() if padrao else None


def limpar_url(url: str) -> str:
    """Constrói URL limpo amazon.es/dp/ASIN sem parâmetros."""
    asin = extrair_asin(url)
    if asin:
        return f"https://www.amazon.es/dp/{asin}"
    return url


def gerar_link_afiliado(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}?tag={ASSOCIATE_TAG}"


def resolver_e_limpar(url_curto: str) -> tuple[str, str | None]:
    """
    Resolve amzn.to → URL completo → extrai ASIN → URL limpo.
    Devolve (url_limpo, asin).
    """
    try:
        session = requests.Session()
        resp = session.get(
            url_curto,
            headers=random.choice(HEADERS_LIST),
            allow_redirects=True,
            timeout=15
        )
        url_resolvido = resp.url
        print(f"  → Resolvido: {url_resolvido[:80]}")

        asin = extrair_asin(url_resolvido)
        if not asin:
            # Tenta extrair do histórico de redirects
            for r in resp.history:
                asin = extrair_asin(r.url)
                if asin:
                    break

        if asin:
            url_limpo = f"https://www.amazon.es/dp/{asin}"
            print(f"  → URL limpo: {url_limpo}")
            return url_limpo, asin
        else:
            print(f"  ⚠️ ASIN não encontrado no URL resolvido")
            return url_resolvido, None

    except Exception as e:
        print(f"  ⚠️ Erro ao resolver: {e}")
        return url_curto, None


def limpar_preco(texto: str) -> str:
    """Extrai número do preço, ex: '39,99 €' → '39.99'"""
    texto = texto.replace("\xa0", " ").replace("€", "").strip()
    padrao = re.search(r"(\d+)[,.](\d{2})", texto)
    if padrao:
        return f"{padrao.group(1)}.{padrao.group(2)}"
    padrao2 = re.search(r"(\d+)", texto)
    if padrao2:
        return padrao2.group(1)
    return ""


def fazer_scraping(url_limpo: str) -> dict | None:
    """Faz scraping da página produto Amazon com URL limpo."""
    try:
        time.sleep(random.uniform(3, 6))
        session = requests.Session()
        headers = random.choice(HEADERS_LIST)
        headers["Referer"] = "https://www.amazon.es/"

        resp = session.get(url_limpo, headers=headers, timeout=20)
        print(f"  → HTTP status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"  ⚠️ Página não acessível (status {resp.status_code})")
            return None

        # Verifica se foi redirecccionado para CAPTCHA
        if "robot" in resp.url or "captcha" in resp.text.lower()[:500]:
            print(f"  ⚠️ CAPTCHA detectado — Amazon bloqueou o pedido")
            return None

        soup = BeautifulSoup(resp.content, "html.parser")

        dados = {}

        # ── Título ──────────────────────────────────────────
        seletores_titulo = [
            ("span", {"id": "productTitle"}),
            ("span", {"id": "title"}),
            ("h1",   {"id": "title"}),
            ("h1",   {"class": "a-size-large"}),
        ]
        titulo_el = None
        for tag, attrs in seletores_titulo:
            titulo_el = soup.find(tag, attrs)
            if titulo_el:
                break

        if not titulo_el:
            titulo_el = soup.find("h1")

        if not titulo_el:
            print(f"  ⚠️ Título não encontrado")
            # Debug: mostra o início do HTML para diagnóstico
            print(f"  Debug HTML: {resp.text[:300]}")
            return None

        dados["titulo"] = titulo_el.get_text().strip()[:150]
        print(f"  → Título: {dados['titulo'][:60]}")

        # ── Preço actual ─────────────────────────────────────
        preco_str = ""

        # Método 1: bloco de preço principal
        preco_bloco = soup.find("span", {"class": "a-price"})
        if preco_bloco:
            offscreen = preco_bloco.find("span", {"class": "a-offscreen"})
            if offscreen:
                preco_str = limpar_preco(offscreen.get_text())

        # Método 2: preço inteiro + fracção
        if not preco_str:
            whole = soup.find("span", {"class": "a-price-whole"})
            frac  = soup.find("span", {"class": "a-price-fraction"})
            if whole:
                w = whole.get_text().strip().replace(".", "").replace(",", "")
                f = frac.get_text().strip() if frac else "00"
                preco_str = f"{w}.{f}"

        # Método 3: IDs específicos
        if not preco_str:
            for id_preco in ["priceblock_ourprice", "priceblock_dealprice",
                              "priceblock_saleprice"]:
                el = soup.find("span", {"id": id_preco})
                if el:
                    preco_str = limpar_preco(el.get_text())
                    break

        dados["preco"] = preco_str
        print(f"  → Preço: {preco_str}")

        # ── Preço anterior (riscado) ──────────────────────────
        preco_ant_str = ""

        seletores_ant = [
            ("span", {"class": "a-price a-text-price"}),
            ("span", {"data-a-strike": "true"}),
            ("span", {"class": "priceBlockStrikePriceString"}),
            ("span", {"id": "listPrice"}),
        ]
        for tag, attrs in seletores_ant:
            el = soup.find(tag, attrs)
            if el:
                offscreen = el.find("span", {"class": "a-offscreen"})
                texto = offscreen.get_text() if offscreen else el.get_text()
                preco_ant_str = limpar_preco(texto)
                if preco_ant_str:
                    break

        dados["preco_anterior"] = preco_ant_str
        print(f"  → Preço anterior: {preco_ant_str}")

        # ── Desconto ─────────────────────────────────────────
        desconto_str = "0"
        if dados["preco"] and dados["preco_anterior"]:
            try:
                p  = float(dados["preco"])
                pa = float(dados["preco_anterior"])
                if pa > p > 0:
                    desconto_str = str(round((1 - p / pa) * 100))
            except ValueError:
                pass

        if desconto_str == "0":
            badge = soup.find("span", {"class": "savingsPercentage"})
            if badge:
                desconto_str = badge.get_text().replace(
                    "-", "").replace("%", "").strip()

        dados["desconto"] = desconto_str
        print(f"  → Desconto: {desconto_str}%")

        # ── Imagem ───────────────────────────────────────────
        imagem_url = ""
        img_el = (
            soup.find("img", {"id": "landingImage"}) or
            soup.find("img", {"id": "imgBlkFront"}) or
            soup.find("img", {"id": "main-image"})
        )
        if img_el:
            imagem_url = (
                img_el.get("data-old-hires") or
                img_el.get("src", "")
            )
            # data-a-dynamic-image é JSON com URLs
            dynamic = img_el.get("data-a-dynamic-image", "")
            if dynamic:
                urls = re.findall(r'"(https://[^"]+\.jpg[^"]*)"', dynamic)
                if urls:
                    # Escolhe a maior (último par largura/altura)
                    imagem_url = urls[-1]

        dados["imagem"] = imagem_url
        print(f"  → Imagem: {'OK' if imagem_url else 'não encontrada'}")

        # ── Características ──────────────────────────────────
        caracteristicas = []
        bullets = soup.find("div", {"id": "feature-bullets"})
        if bullets:
            items = bullets.find_all("span", {"class": "a-list-item"})
            for item in items:
                texto = item.get_text().strip()
                if texto and len(texto) > 10:
                    caracteristicas.append(texto[:90])
                if len(caracteristicas) >= 3:
                    break

        dados["caracteristicas"] = caracteristicas

        return dados

    except Exception as e:
        print(f"  ⚠️ Erro no scraping: {e}")
        return None


def main():
    if not os.path.exists(FICHEIRO_LINKS):
        print(f"⚠️ {FICHEIRO_LINKS} não encontrado.")
        return

    with open(FICHEIRO_LINKS, "r", encoding="utf-8") as f:
        links = [l.strip() for l in f if l.strip() and l.startswith("http")]

    if not links:
        print("⚠️ Nenhum link em links.txt.")
        return

    print(f"🔄 A processar {len(links)} link(s)...")

    produtos = []
    for i, link_curto in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] {link_curto}")

        url_limpo, asin = resolver_e_limpar(link_curto)

        if not asin:
            print(f"  ❌ Não foi possível extrair ASIN.")
            continue

        link_afiliado = gerar_link_afiliado(asin)
        dados = fazer_scraping(url_limpo)

        if not dados:
            print(f"  ❌ Scraping falhou.")
            continue

        if not dados.get("preco"):
            print(f"  ⚠️ Preço não encontrado, a ignorar.")
            continue

        produto = {
            "titulo":          dados["titulo"],
            "preco":           dados["preco"],
            "preco_anterior":  dados["preco_anterior"],
            "desconto":        dados["desconto"],
            "imagem":          dados["imagem"],
            "link":            link_afiliado,
            "caracteristica1": dados["caracteristicas"][0] if len(dados["caracteristicas"]) > 0 else "",
            "caracteristica2": dados["caracteristicas"][1] if len(dados["caracteristicas"]) > 1 else "",
            "caracteristica3": dados["caracteristicas"][2] if len(dados["caracteristicas"]) > 2 else "",
        }
        produtos.append(produto)
        print(f"  ✅ Produto extraído com sucesso!")

    if not produtos:
        print("\n⚠️ Nenhum produto extraído.")
        return

    # Escreve no CSV
    ficheiro_existe = os.path.exists(FICHEIRO_CSV)
    tem_conteudo = False
    if ficheiro_existe:
        with open(FICHEIRO_CSV, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            tem_conteudo = len(conteudo) > len(",".join(CABECALHO))

    with open(FICHEIRO_CSV, "a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CABECALHO)
        if not tem_conteudo:
            escritor.writeheader()
        escritor.writerows(produtos)

    # Limpa links.txt
    with open(FICHEIRO_LINKS, "w", encoding="utf-8") as f:
        f.write("")

    print(f"\n🎉 {len(produtos)} produto(s) adicionados ao CSV.")


if __name__ == "__main__":
    main()
