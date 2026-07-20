# scraper.py
"""
Lê links.txt, resolve links amzn.to para amazon.es,
faz scraping de cada produto e gera produtos_novos.csv.
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

ASSOCIATE_TAG   = os.getenv("AMAZON_ASSOCIATE_TAG", "")
FICHEIRO_LINKS  = "links.txt"
FICHEIRO_CSV    = "produtos_novos.csv"
CABECALHO       = [
    "titulo", "preco", "preco_anterior", "desconto",
    "imagem", "link",
    "caracteristica1", "caracteristica2", "caracteristica3"
]

# Headers para simular um browser real
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
]


def resolver_link(url_curto: str) -> str:
    """Resolve amzn.to para o URL completo amazon.es."""
    try:
        resp = requests.get(
            url_curto,
            headers=random.choice(HEADERS_LIST),
            allow_redirects=True,
            timeout=15
        )
        return resp.url
    except Exception as e:
        print(f"⚠️ Erro ao resolver {url_curto}: {e}")
        return url_curto


def extrair_asin(url: str) -> str | None:
    """Extrai o ASIN do URL completo."""
    padrao = re.search(
        r"/(?:dp|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE
    )
    return padrao.group(1).upper() if padrao else None


def gerar_link_afiliado(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}?tag={ASSOCIATE_TAG}"


def limpar_preco(texto: str) -> str:
    """Extrai apenas o número do texto do preço."""
    texto = texto.replace("\xa0", " ").strip()
    padrao = re.search(r"[\d]+[.,][\d]+", texto)
    return padrao.group(0).replace(",", ".") if padrao else ""


def fazer_scraping(url_completo: str) -> dict | None:
    """Faz scraping da página do produto Amazon."""
    try:
        time.sleep(random.uniform(2, 5))  # pausa aleatória entre pedidos
        headers = random.choice(HEADERS_LIST)
        resp = requests.get(url_completo, headers=headers, timeout=15)

        if resp.status_code != 200:
            print(f"⚠️ Status {resp.status_code} para {url_completo}")
            return None

        soup = BeautifulSoup(resp.content, "html.parser")

        dados = {}

        # Título
        titulo_el = (
            soup.find("span", {"id": "productTitle"}) or
            soup.find("h1", {"id": "title"})
        )
        if not titulo_el:
            print(f"⚠️ Título não encontrado: {url_completo}")
            return None
        dados["titulo"] = titulo_el.get_text().strip()[:150]

        # Preço actual
        preco_el = (
            soup.find("span", {"class": "a-price-whole"}) or
            soup.find("span", {"id": "priceblock_ourprice"}) or
            soup.find("span", {"id": "priceblock_dealprice"}) or
            soup.find("span", {"class": "a-offscreen"})
        )
        if preco_el:
            preco_texto = preco_el.get_text().strip()
            # Tenta também apanhar os decimais
            preco_frac = soup.find("span", {"class": "a-price-fraction"})
            if preco_frac and "a-price-whole" in str(preco_el):
                preco_texto = preco_texto.rstrip(".") + "." + preco_frac.get_text().strip()
            dados["preco"] = limpar_preco(preco_texto)
        else:
            dados["preco"] = ""

        # Preço anterior (riscado)
        preco_ant_el = (
            soup.find("span", {"class": "a-price a-text-price"}) or
            soup.find("span", {"data-a-strike": "true"}) or
            soup.find("span", {"class": "priceBlockStrikePriceString"})
        )
        if preco_ant_el:
            span = preco_ant_el.find("span", {"class": "a-offscreen"})
            texto_ant = span.get_text() if span else preco_ant_el.get_text()
            dados["preco_anterior"] = limpar_preco(texto_ant)
        else:
            dados["preco_anterior"] = ""

        # Desconto
        if dados["preco"] and dados["preco_anterior"]:
            try:
                p = float(dados["preco"])
                pa = float(dados["preco_anterior"])
                if pa > p > 0:
                    dados["desconto"] = str(round((1 - p / pa) * 100))
                else:
                    dados["desconto"] = "0"
            except ValueError:
                dados["desconto"] = "0"
        else:
            # Tenta apanhar o badge de desconto directamente
            badge = soup.find("span", {"class": "savingsPercentage"})
            if badge:
                dados["desconto"] = badge.get_text().replace("-", "").replace("%", "").strip()
            else:
                dados["desconto"] = "0"

        # Imagem principal
        img_el = soup.find("img", {"id": "landingImage"}) or \
                 soup.find("img", {"id": "imgBlkFront"}) or \
                 soup.find("img", {"class": "a-dynamic-image"})
        if img_el:
            # Tenta obter a imagem de maior resolução
            src = img_el.get("data-old-hires") or \
                  img_el.get("data-a-dynamic-image") or \
                  img_el.get("src", "")
            # data-a-dynamic-image é um JSON com URLs — apanha o primeiro
            if src.startswith("{"):
                urls = re.findall(r'"(https://[^"]+)"', src)
                src = urls[0] if urls else ""
            dados["imagem"] = src
        else:
            dados["imagem"] = ""

        # Características (bullet points)
        bullets = soup.find("div", {"id": "feature-bullets"})
        caracteristicas = []
        if bullets:
            items = bullets.find_all("span", {"class": "a-list-item"})
            for item in items:
                texto = item.get_text().strip()
                if texto and len(texto) > 10 and "Ver mais" not in texto:
                    caracteristicas.append(texto[:90])
                if len(caracteristicas) >= 3:
                    break
        dados["caracteristicas"] = caracteristicas

        return dados

    except Exception as e:
        print(f"⚠️ Erro no scraping de {url_completo}: {e}")
        return None


def main():
    if not os.path.exists(FICHEIRO_LINKS):
        print(f"⚠️ Ficheiro {FICHEIRO_LINKS} não encontrado.")
        return

    with open(FICHEIRO_LINKS, "r", encoding="utf-8") as f:
        links = [l.strip() for l in f if l.strip() and l.startswith("http")]

    if not links:
        print("⚠️ Nenhum link encontrado no links.txt.")
        return

    print(f"🔄 A processar {len(links)} links...")

    # Carrega CSV existente para evitar duplicados
    links_existentes = set()
    if os.path.exists(FICHEIRO_CSV):
        with open(FICHEIRO_CSV, "r", encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            for linha in leitor:
                if linha.get("link"):
                    links_existentes.add(linha["link"])

    produtos = []
    for i, link_curto in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] A processar: {link_curto}")

        # Resolve o link curto
        url_completo = resolver_link(link_curto)
        print(f"  → Resolvido: {url_completo[:80]}")

        # Extrai ASIN e gera link de afiliado
        asin = extrair_asin(url_completo)
        if not asin:
            print(f"  ⚠️ ASIN não encontrado, a ignorar.")
            continue

        link_afiliado = gerar_link_afiliado(asin)

        if link_afiliado in links_existentes:
            print(f"  ⏭️ Já existe no CSV, a ignorar.")
            continue

        # Scraping
        dados = fazer_scraping(url_completo)
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
        links_existentes.add(link_afiliado)
        print(f"  ✅ OK: {dados['titulo'][:50]}")
        print(f"     Preço: {dados['preco']} € | Antes: {dados['preco_anterior']} € | Desconto: {dados['desconto']}%")

    if not produtos:
        print("\n⚠️ Nenhum produto extraído com sucesso.")
        return

    # Escreve no CSV
    ficheiro_existe = os.path.exists(FICHEIRO_CSV)
    tem_cabecalho = False
    if ficheiro_existe:
        with open(FICHEIRO_CSV, "r", encoding="utf-8") as f:
            primeira_linha = f.readline().strip()
            tem_cabecalho = primeira_linha == ",".join(CABECALHO)

    with open(FICHEIRO_CSV, "a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CABECALHO)
        if not tem_cabecalho:
            escritor.writeheader()
        escritor.writerows(produtos)

    # Limpa o links.txt
    with open(FICHEIRO_LINKS, "w", encoding="utf-8") as f:
        f.write("")

    print(f"\n🎉 {len(produtos)} produto(s) adicionados ao CSV.")
    print(f"📄 links.txt limpo.")
    print(f"▶️  Corre agora o workflow 'Importar Produtos do CSV'.")


if __name__ == "__main__":
    main()
