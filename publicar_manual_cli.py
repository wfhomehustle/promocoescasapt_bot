# publicar_manual_cli.py
"""
Versão do publicar_manual.py que lê os dados de variáveis de
ambiente — usado pelo workflow 'Publicar Manual' do GitHub Actions.
"""

import os
from gerador_imagem import criar_imagem_oferta, guardar_imagem
from bot_telegram import publicar_oferta

preco_anterior = os.getenv("PRECO_ANTERIOR", "").strip()

caracteristicas = []
for i in range(1, 4):
    c = os.getenv(f"CARACTERISTICA{i}", "").strip()
    if c:
        caracteristicas.append(c)

oferta = {
    "asin": os.getenv("ASIN"),
    "titulo": os.getenv("TITULO"),
    "preco": os.getenv("PRECO"),
    "preco_anterior": preco_anterior if preco_anterior else None,
    "desconto": int(os.getenv("DESCONTO", "0")),
    "imagem": os.getenv("IMAGEM"),
    "link": os.getenv("LINK"),
    "caracteristicas": caracteristicas,
}

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
    print(f"✅ Publicado: {oferta['titulo'][:50]}")
else:
    print("❌ Falhou")
