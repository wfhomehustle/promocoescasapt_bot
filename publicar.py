# publicar.py
import os
import time
from produtos import procurar_ofertas
from gerador_imagem import criar_imagem_oferta, guardar_imagem
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
        return

    publicadas_agora = 0
    for oferta in novas:
        if publicadas_agora >= NUM_OFERTAS_POR_EXECUCAO:
            break

        imagem  = criar_imagem_oferta(
            titulo            = oferta.get("titulo", ""),
            preco_anterior    = oferta.get("preco_anterior"),
            preco_promo       = oferta.get("preco", ""),
            desconto_pct      = oferta.get("desconto", 0),
            url_imagem_produto= oferta.get("imagem"),
        )
        caminho = guardar_imagem(imagem, oferta["asin"])
        sucesso = publicar_oferta(oferta, caminho)

        try:
            os.remove(caminho)
        except OSError:
            pass

        if sucesso:
            guardar_publicado(oferta["asin"])
            publicadas_agora += 1
            time.sleep(5)


if __name__ == "__main__":
    main()
