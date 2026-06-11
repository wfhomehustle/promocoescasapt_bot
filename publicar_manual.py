# publicar_manual.py
"""
Modo manual — usa enquanto não tens acesso à PA-API.
Recolhe os dados via SiteStripe (amazon.es) e preenche aqui.
Cada publicação ajuda a atingir as 3 vendas necessárias para
ativar a PA-API.
"""

import os
from gerador_imagem import criar_imagem_oferta, guardar_imagem
from bot_telegram import publicar_oferta

# ──────────────────────────────────────────────────────────────
# PREENCHE OS DADOS DO PRODUTO AQUI (recolhidos via SiteStripe)
# ──────────────────────────────────────────────────────────────

oferta = {
    "asin": "B0001",  # podes usar qualquer código único, ex: B0001, B0002...
    "titulo": "Roborock Robot Aspirador QV 35A, 8000Pa de sucção",
    "preco": "335,45 €",            # preço atual (cola da página do produto)
    "preco_anterior": "599,75 €",   # preço riscado (deixa "" se não houver)
    "desconto": 44,                # calcula: (1 - 39.99/59.99) * 100, arredonda
    "imagem": "https://m.media-amazon.com/images/I/61RJLs+bX7L._AC_SL1500_.jpg",   # botão "Imagem" na SiteStripe
    "link": "https://amzn.to/4v5ocDo",          # botão "Texto" na SiteStripe
    "caracteristicas": [
        "Duas mopas giratórias e ajustáveis",
        "escovas anti-emaranhados",
        "Tecnologia reativa para evitar obstáculos",
    ],
}

# ──────────────────────────────────────────────────────────────
# NÃO PRECISAS DE MEXER DAQUI PARA BAIXO
# ──────────────────────────────────────────────────────────────

if oferta["preco_anterior"] == "":
    oferta["preco_anterior"] = None

imagem = criar_imagem_oferta(
    titulo=oferta["titulo"],
    preco_anterior=oferta["preco_anterior"],
    preco_promo=oferta["preco"],
    desconto_pct=oferta["desconto"],
    url_imagem_produto=oferta["imagem"],
)
caminho = guardar_imagem(imagem, oferta["asin"])

sucesso = publicar_oferta(oferta, caminho)

try:
    os.remove(caminho)
except OSError:
    pass

if sucesso:
    print(f"✅ Publicado com sucesso: {oferta['titulo'][:50]}")
else:
    print("❌ Falhou — revê o token/canal no .env")
