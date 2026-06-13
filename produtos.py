# produtos.py
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


def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _assinar_pedido(payload: str) -> dict:
    t = datetime.datetime.utcnow()
    amz_date   = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

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
    signed_headers    = ";".join(k for k, _ in sorted_headers)

    canonical_request = (
        f"POST\n{ENDPOINT_PATH}\n\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm        = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign   = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    k_date    = _sign(("AWS4" + SECRET_KEY).encode("utf-8"), date_stamp)
    k_region  = _sign(k_date, REGION)
    k_service = _sign(k_region, SERVICE)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return {
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8",
        "Host": HOST,
        "X-Amz-Date": amz_date,
        "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={ACCESS_KEY}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }


def procurar_ofertas(max_resultados: int = 5) -> list[dict]:
    pesquisa, categoria = random.choice(PESQUISAS)

    payload_dict = {
        "Keywords":    pesquisa,
        "SearchIndex": categoria,
        "ItemCount":   max_resultados,
        "PartnerTag":  ASSOCIATE_TAG,
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
    except Exception as e:
        print(f"Erro ao contactar a Amazon: {e}")
        return []

    ofertas = []
    for item in data.get("SearchResult", {}).get("Items", []):
        asin = item.get("ASIN")
        if not asin:
            continue

        oferta = {"asin": asin, "link": gerar_link_afiliado(asin)}

        titulo = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue")
        if not titulo:
            continue
        oferta["titulo"] = titulo

        listings = item.get("Offers", {}).get("Listings", [])
        if listings:
            price_info = listings[0].get("Price", {})
            oferta["preco"] = price_info.get("DisplayAmount", "Ver preço")
            preco_valor     = price_info.get("Amount")
            saving          = listings[0].get("SavingBasis")
            if saving:
                oferta["preco_anterior"] = saving.get("DisplayAmount")
                anterior_valor = saving.get("Amount")
                oferta["desconto"] = (
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

        imagem = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")
        oferta["imagem"] = imagem

        features = item.get("ItemInfo", {}).get("Features", {}).get("DisplayValues", [])
        oferta["caracteristicas"] = features[:3]

        if oferta["desconto"] >= 10:
            ofertas.append(oferta)

    return ofertas
