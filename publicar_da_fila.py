# publicar_da_fila.py
import os
from gerador_imagem import criar_todas_imagens, guardar_imagem, guardar_todas_imagens
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
imagens  = criar_todas_imagens(
    titulo, preco_anterior, preco_promo,
    desconto_pct, url_imagem
)

# Guarda temporariamente em /tmp
caminhos = guardar_todas_imagens(imagens, asin, pasta="/tmp")

# Publica no Telegram (formato quadrado)
caminho_telegram = caminhos.get("quadrada")
if caminho_telegram:
    sucesso = publicar_oferta(produto, caminho_telegram)
    if sucesso:
        print(f"✅ Publicado no Telegram: {titulo[:50]}")

# Guarda imagens no repositório para as redes sociais
PASTA_SOCIAL = "imagens_sociais"
os.makedirs(PASTA_SOCIAL, exist_ok=True)

caminhos_sociais = {}
for formato in ["quadrada", "pinterest", "story"]:
    caminho_tmp = caminhos.get(formato)
    if caminho_tmp and os.path.exists(caminho_tmp):
        destino = f"{PASTA_SOCIAL}/{asin}_{formato}.jpg"
        with open(caminho_tmp, "rb") as f_in, open(destino, "wb") as f_out:
            f_out.write(f_in.read())
        caminhos_sociais[formato] = destino
        print(f"📁 Imagem guardada: {destino}")

# Guarda metadados do produto em JSON para o Make.com ler
import json
PASTA_META = "metadados_sociais"
os.makedirs(PASTA_META, exist_ok=True)

metadados = {
    "asin":           asin,
    "titulo":         titulo,
    "preco":          preco_promo,
    "preco_anterior": preco_anterior or "",
    "desconto":       desconto_pct,
    "link":           produto.get("link", ""),
    "imagem_quadrada":  f"imagens_sociais/{asin}_quadrada.jpg",
    "imagem_pinterest": f"imagens_sociais/{asin}_pinterest.jpg",
    "imagem_story":     f"imagens_sociais/{asin}_story.jpg",
    "caracteristicas":  produto.get("caracteristicas", []),
}

with open(f"{PASTA_META}/{asin}.json", "w", encoding="utf-8") as f:
    json.dump(metadados, f, ensure_ascii=False, indent=2)
print(f"📋 Metadados guardados: {PASTA_META}/{asin}.json")

# Limpa /tmp
for caminho in caminhos.values():
    try:
        os.remove(caminho)
    except OSError:
        pass
