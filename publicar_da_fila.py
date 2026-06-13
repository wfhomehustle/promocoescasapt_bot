# publicar_da_fila.py
import os
from gerador_imagem import criar_imagem_oferta, guardar_imagem
from bot_telegram import publicar_oferta
from fila_manager import retirar_proximo

produto = retirar_proximo()

if not produto:
    print("ℹ️ Fila vazia — nada para publicar.")
    exit(0)

imagem  = criar_imagem_oferta(
    titulo            = produto["titulo"],
    preco_anterior    = produto.get("preco_anterior"),
    preco_promo       = produto["preco"],
    desconto_pct      = int(produto.get("desconto", 0)),
    url_imagem_produto= produto.get("imagem"),
)
caminho = guardar_imagem(imagem, produto["asin"])
sucesso = publicar_oferta(produto, caminho)

try:
    os.remove(caminho)
except OSError:
    pass

if sucesso:
    print(f"✅ Publicado: {produto['titulo'][:50]}")
