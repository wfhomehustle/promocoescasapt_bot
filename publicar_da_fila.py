# publicar_da_fila.py
import os
from gerador_imagem import criar_imagem_quadrada, criar_todas_imagens, guardar_imagem, guardar_todas_imagens
from bot_telegram import publicar_oferta
from fila_manager import retirar_proximo

produto = retirar_proximo()

if not produto:
    print("ℹ️ Fila vazia — nada para publicar.")
    exit(0)

titulo         = produto["titulo"]
preco_anterior = produto.get("preco_anterior")
preco_promo    = produto["preco"]
desconto_pct   = int(produto.get("desconto", 0))
url_imagem     = produto.get("imagem")
asin           = produto["asin"]

# Gera os 3 formatos
imagens  = criar_todas_imagens(titulo, preco_anterior, preco_promo,
                                desconto_pct, url_imagem)

# Guarda todos em /tmp
caminhos = guardar_todas_imagens(imagens, asin, pasta="/tmp")

# Publica no Telegram (formato quadrado)
caminho_telegram = caminhos.get("quadrada")
if caminho_telegram:
    sucesso = publicar_oferta(produto, caminho_telegram)
    if sucesso:
        print(f"✅ Publicado no Telegram: {titulo[:50]}")

# Guarda Pinterest e Story como artefactos do GitHub Actions
# para fazeres download e usares nas redes sociais
for formato in ["pinterest", "story"]:
    caminho = caminhos.get(formato)
    if caminho:
        # Copia para pasta raiz do projecto (fica acessível nos artefactos)
        destino = f"imagens_sociais/oferta_{asin}_{formato}.jpg"
        os.makedirs("imagens_sociais", exist_ok=True)
        with open(caminho, "rb") as f_in, open(destino, "wb") as f_out:
            f_out.write(f_in.read())
        print(f"📁 Guardado para redes sociais: {destino}")

# Limpa /tmp
for caminho in caminhos.values():
    try:
        os.remove(caminho)
    except OSError:
        pass
