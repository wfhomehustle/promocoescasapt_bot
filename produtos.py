# produtos.py
"""
Procura ofertas usando a Amazon Creators API (OAuth 2.0).
Substitui a PA-API 5.0 que foi descontinuada em Maio 2026.
"""

import os
import json
import random
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("AMAZON_ACCESS_KEY")
CLIENT_SECRET = os.getenv("AMAZON_SECRET_KEY")
ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG")

# URLs da Creators API
TOKEN_URL    = "https://api.amazon.com/auth/o2/token"
API_BASE_URL = "https://creatorsapi.amazon/catalog/v1"

PESQUISAS = [
    ("fritadeira sem óleo",          "Kitchen"),
    ("robot de cozinha",             "Kitchen"),
    ("máquina de café",              "Kitchen"),
    ("aspirador vertical",           "Home"),
    ("robot aspirador",              "Home"),
    ("organizadores de cozinha",     "Home"),
    ("auriculares bluetooth",        "Electronics"),
    ("smartwatch oferta",            "Electronics"),
    ("tablet oferta",                "Electronics"),
    ("livros mais vendidos",         "Books"),
    ("brinquedos promoção",          "Toys"),
    ("roupa desportiva",             "Apparel"),
    ("perfume mulher oferta",        "Beauty"),
    ("caixas de arrumação",          "Home"),
    ("conjunto de panelas",          "Kitchen"),
    ("máquina de fazer pão",         "Kitchen"),
    ("ferro de engomar a vapor",     "Home"),
    ("prateleiras de armazenamento", "Home"),
    ("câmara de vigilância",         "Electronics"),
    ("colchão viscoelástico",        "Home"),
]


def gerar_link_afiliado(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}?tag={ASSOCIATE_TAG}"


def obter_token() -> str | None:
    """Obtém token de acesso OAuth 2.0 para a Creators API."""
    try:
        # Tenta primeiro com form-urlencoded (formato standard OAuth 2.0)
        resp = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "client_credentials",
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope":         "creatorsapi::default",
            },
            timeout=15
        )

        if resp.status_code == 400:
            # Fallback: tenta com JSON
            print(f"   Form-urlencoded falhou ({resp.status_code}), a tentar JSON...")
            resp = requests.post(
                TOKEN_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type":    "client_credentials",
                    "client_id":     CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "scope":         "creatorsapi::default",
                },
                timeout=15
            )

        resp.raise_for_status()
        token = resp.json().get("access_token")
        print(f"✅ Token OAuth obtido com sucesso")
        return token

    except Exception as e:
        print(f"❌ Erro ao obter token OAuth: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Resposta: {e.response.text[:500]}")
        return None


def procurar_ofertas(max_resultados: int = 5) -> list[dict]:
    """Procura ofertas via Amazon Creators API."""

    token = obter_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "x-marketplace": "www.amazon.es",
    }

    pesquisa, categoria = random.choice(PESQUISAS)

    payload = {
        "keywords":         pesquisa,
        "searchIndex":      categoria,
        "itemCount":        max_resultados,
        "partnerTag":       ASSOCIATE_TAG,
        "partnerType":      "Associates",
        "marketplace":      "www.amazon.es",
        "resources": [
            "itemInfo.title",
            "offers.listingsV2.price",
            "offers.listingsV2.savingBasis",
            "images.primary.large",
            "itemInfo.features",
        ],
        "minSavingPercent": 10,
    }

    try:
        resp = requests.post(
            f"{API_BASE_URL}/searchItems",
            headers=headers,
            json=payload,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Erro na Creators API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Resposta: {e.response.text[:500]}")
        return []

    ofertas = []
    items = data.get("searchResult", {}).get("items", [])

    for item in items:
        asin = item.get("asin")
        if not asin:
            continue

        oferta = {"asin": asin, "link": gerar_link_afiliado(asin)}

        # Título
        titulo = (item.get("itemInfo", {})
                     .get("title", {})
                     .get("displayValue"))
        if not titulo:
            continue
        oferta["titulo"] = titulo

        # Preços (formato listingsV2)
        listings = (item.get("offers", {})
                       .get("listingsV2", []))
        if listings:
            price_info = listings[0].get("price", {})
            oferta["preco"]  = price_info.get("displayAmount", "Ver preço")
            preco_valor      = price_info.get("amount")
            saving           = listings[0].get("savingBasis")
            if saving:
                oferta["preco_anterior"] = saving.get("displayAmount")
                anterior_valor           = saving.get("amount")
                oferta["desconto"]       = (
                    round((1 - preco_valor / anterior_valor) * 100)
                    if preco_valor and anterior_valor else 0
                )
            else:
                oferta["preco_anterior"] = None
                oferta["desconto"]       = 0
        else:
            oferta["preco"]          = "Ver preço"
            oferta["preco_anterior"] = None
            oferta["desconto"]       = 0

        # Imagem
        imagem = (item.get("images", {})
                     .get("primary", {})
                     .get("large", {})
                     .get("url"))
        oferta["imagem"] = imagem

        # Características
        features = (item.get("itemInfo", {})
                       .get("features", {})
                       .get("displayValues", []))
        oferta["caracteristicas"] = features[:3]

        if oferta["desconto"] >= 10:
            ofertas.append(oferta)

    print(f"✅ {len(ofertas)} oferta(s) encontrada(s)")
    return ofertas
