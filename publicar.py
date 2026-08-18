# publicar.py
import os
import time
import json
from produtos import procurar_ofertas
from gerador_imagem import criar_todas_imagens, guardar_imagem, guardar_todas_imagens
from bot_telegram import publicar_oferta

PASTA_DADOS             = os.path.dirname(os.path.abspath(__file__))
FICHEIRO_PUBLICADOS     = os.path.join(PASTA_DADOS, "publicados.txt")
NUM_OFERTAS_POR_EXECUCAO = 2


def carregar_publicados() -> set:
    if not os.path.exists(FICHEIRO_PUBLICADOS):
        return set()
    with open(FICHEIRO_PUBLICADOS, "r") as f:
        return set(linha.strip() for linha in f if linha.strip())


def guardar_publicado(asin: str) -> None:
    with open(FICHEIRO_PUBLICADOS, "a") as f:
        f.write(asin + "\n")


def main():
    publicados = carregar_publicados()
    ofertas    = procurar_ofertas(max_resultados=10)
    novas      = [o for o in ofertas if o["asin"] not in publicados]

    if not novas:
        print("ℹ️ Sem ofertas novas.")
        return

    publicadas_agora = 0
    for oferta in novas:
        if publicadas_agora >= NUM_OFERTAS_POR_EXECUCAO:
            break

        asin           = oferta["asin"]
        titulo         = oferta.get("titulo", "")
        preco_anterior = oferta.get("preco_anterior")
        preco_promo    = oferta.get("preco", "")
        desconto_pct   = oferta.get("desconto", 0)
        url_imagem     = oferta.get("imagem")

        # Gera os 3 formatos de imagem
        imagens  = criar_todas_imagens(
            titulo, preco_anterior, preco_promo,
            desconto_pct, url_imagem
        )

        # Guarda temporariamente em /tmp
        caminhos = guardar_todas_imagens(imagens, asin, pasta="/tmp")

        # Publica no Telegram
        caminho_telegram = caminhos.get("quadrada")
        if caminho_telegram:
            sucesso = publicar_oferta(oferta, caminho_telegram)
        else:
            sucesso = False

        if sucesso:
            # Guarda imagens no repositório para redes sociais
            PASTA_SOCIAL = "imagens_sociais"
            os.makedirs(PASTA_SOCIAL, exist_ok=True)

            for formato in ["quadrada", "pinterest", "story"]:
                caminho_tmp = caminhos.get(formato)
                if caminho_tmp and os.path.exists(caminho_tmp):
                    destino = f"{PASTA_SOCIAL}/{asin}_{formato}.jpg"
                    with open(caminho_tmp, "rb") as f_in, open(destino, "wb") as f_out:
                        f_out.write(f_in.read())

            # Guarda metadados para o Make.com
            PASTA_META = "metadados_sociais"
            os.makedirs(PASTA_META, exist_ok=True)

            metadados = {
                "asin":             asin,
                "titulo":           titulo,
                "preco":            preco_promo,
                "preco_anterior":   preco_anterior or "",
                "desconto":         desconto_pct,
                "link":             oferta.get("link", ""),
                "imagem_quadrada":  f"imagens_sociais/{asin}_quadrada.jpg",
                "imagem_pinterest": f"imagens_sociais/{asin}_pinterest.jpg",
                "imagem_story":     f"imagens_sociais/{asin}_story.jpg",
                "caracteristicas":  oferta.get("caracteristicas", []),
            }

            with open(f"{PASTA_META}/{asin}.json", "w", encoding="utf-8") as f:
                json.dump(metadados, f, ensure_ascii=False, indent=2)

            guardar_publicado(asin)
            publicadas_agora += 1

        # Limpa /tmp
        for caminho in caminhos.values():
            try:
                os.remove(caminho)
            except OSError:
                pass

        if publicadas_agora < NUM_OFERTAS_POR_EXECUCAO:
            time.sleep(5)


if __name__ == "__main__":
    main()
