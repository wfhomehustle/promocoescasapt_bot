# produtos.py
"""
Procura ofertas Casa & Cozinha na Amazon.es usando a PA-API 5.0
diretamente via requests (assinatura AWS V4), sem SDKs externos.
"""

import os
import json
import random
import datetime
import hashlib
import hmac
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY    = os.getenv("AMAZON_ACCESS_KEY")
SECRET_KEY    = os.getenv("AMAZON_SECRET_KEY")
ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG")

HOST    = "webservices.amazon.es"
REGION  = "eu-west-1"
SERVICE = "ProductAdvertisingAPI"
ENDPOINT_PATH = "/paapi5/searchitems"
URI = f"https://{HOST}{ENDPOINT_PATH}"

PESQUISAS = [
    ("fritadeira sem óleo",          "Kitchen"),
    ("robot de cozinha",             "Kitchen"),
    ("máquina de café",              "Kitchen"),
    ("liquidificadora",              "Kitchen"),
    ("torradeira",                   "Kitchen"),
    ("panela elétrica",              "Kitchen"),
    ("aspirador vertical",           "Home"),
    ("robot aspirador",              "Home"),
    ("organizadores de cozinha",     "Home"),
    ("organizadores de armário",     "Home"),
    ("caixas de arrumação",          "Home"),
    ("conjunto de panelas",          "Kitchen"),
    ("faqueiro",                     "Kitchen"),
    ("balança de cozinha",           "Kitchen"),
    ("máquina de fazer pão",         "Kitchen"),
    ("ferro de engomar a vapor",     "Home"),
    ("luminária LED organização",    "Home"),
    ("prateleiras de armazenamento", "Home"),
    ("recipientes herméticos",       "Kitchen"),
    ("difusor de aromas",            "Home"),
]


def gerar_link_afiliado(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}?tag={ASSOCIATE_TAG}"


def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _assinar_pedido(payload: str) -> dict:
    """Gera os cabeçalhos de assinatura AWS V4 para a PA-API."""
    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

    canonical_uri = ENDPOINT_PATH
    canonical_querystring = ""
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    headers_dict = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": HOST,
        "x-amz-date": amz_date,
        "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
    }
    sorted_headers = sorted(headers_dict.items())
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted_headers)
    signed_headers = ";".join(k for k, _ in sorted_headers)

    canonical_request = (
        f"POST\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    k_date    = _sign(("AWS4" + SECRET_KEY).encode("utf-8"), date_stamp)
    k_region  = _sign(k_date, REGION)
    k_service = _sign(k_region, SERVICE)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={ACCESS_KEY}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8",
        "Host": HOST,
        "X-Amz-Date": amz_date,
        "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        "Authorization": authorization_header,
    }


def procurar_ofertas(max_resultados: int = 5) -> list[dict]:
    """Procura ofertas Casa & Cozinha na Amazon.es via PA-API REST."""
    pesquisa, categoria = random.choice(PESQUISAS)

    payload_dict = {
        "Keywords": pesquisa,
        "SearchIndex": categoria,
        "ItemCount": max_resultados,
        "PartnerTag": ASSOCIATE_TAG,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.es",
        "Resources": [
            "ItemInfo.Title",
            "Offers.Listings.Price",
            "Offers.Listings.SavingBasis",
            "Images.Primary.Large",
            "ItemInfo.Features",
        ],
    }
    payload = json.dumps(payload_dict)

    headers = _assinar_pedido(payload)

    try:
        resp = requests.post(URI, headers=headers, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP da Amazon: {e} — Resposta: {resp.text[:500]}")
        return []
    except Exception as e:
        print(f"Erro ao contactar a Amazon: {e}")
        return []

    ofertas = []
    items = data.get("SearchResult", {}).get("Items", [])

    for item in items:
        asin = item.get("ASIN")
        if not asin:
            continue

        oferta = {"asin": asin, "link": gerar_link_afiliado(asin)}

        # Título
        titulo = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue")
        if not titulo:
            continue
        oferta["titulo"] = titulo

        # Preço
        listings = item.get("Offers", {}).get("Listings", [])
        if listings:
            price_info = listings[0].get("Price", {})
            oferta["preco"] = price_info.get("DisplayAmount", "Ver preço")
            preco_valor = price_info.get("Amount")

            saving = listings[0].get("SavingBasis")
            if saving:
                oferta["preco_anterior"] = saving.get("DisplayAmount")
                anterior_valor = saving.get("Amount")
                if preco_valor and anterior_valor:
                    oferta["desconto"] = round((1 - preco_valor / anterior_valor) * 100)
                else:
                    oferta["desconto"] = 0
            else:
                oferta["preco_anterior"] = None
                oferta["desconto"] = 0
        else:
            oferta["preco"] = "Ver preço"
            oferta["preco_anterior"] = None
            oferta["desconto"] = 0

        # Imagem
        imagem = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")
        oferta["imagem"] = imagem

        # Características
        features = item.get("ItemInfo", {}).get("Features", {}).get("DisplayValues", [])
        oferta["caracteristicas"] = features[:3]

        # Só ofertas com desconto real
        if oferta["desconto"] >= 10:
            ofertas.append(oferta)

    return ofertas
