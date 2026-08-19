# publicar.py
import os
import time
import json
from produtos import (procurar_ofertas, carregar_historico,
                      guardar_historico, registar_publicacao,
                      limpar_historico_antigo)
from gerador_imagem import criar_todas_imagens, guardar_todas_imagens
from bot_telegram import publicar_oferta

PASTA_DADOS              = os.path.dirname(os.path.abspath(__file__))
FICHEIRO_PUBLICADOS      = os.path.join(PASTA_DADOS, "publicados.txt")
NUM_OFERTAS_POR_EXECUCAO = 1


def carregar_publicados() -> set:
    if not os.path.exists(FICHEIRO_PUBLICADOS):
        return set()
    with open(FICHEIRO_PUBLICADOS, "r") as f:
        return set(linha.strip() for linha in f if linha.strip())


def guardar_publicado_txt(asin: str) -> None:
    with open(FICHEIRO_PUBLICADOS, "a") as f:
        f.write(asin + "\n")


def main():
    publicados = carregar_publicados()
    ofertas    = procurar_ofertas(max_resultados=10)
    novas      = [o for o in ofertas if o["asin"] not in publicados]

    if not novas:
        print("ℹ️ Sem ofertas novas.")
        return

    historico = carregar_historico()
    historico = limpar_historico_antigo(historico)

    publicadas_agora = 0
    for oferta in novas:
        if publicadas_agora >= NUM_OFERTAS_POR_EXECUCAO:
            break

        asin      = oferta["asin"]
        tipo_deal = oferta.get("tipo_deal", "")

        imagens  = criar_todas_imagens(
            oferta.get("titulo", ""),
            oferta.get("preco_anterior"),
            oferta.get("preco", ""),
            oferta.get("desconto", 0),
            oferta.get("imagem"),
            tipo_deal=tipo_deal,
        )
        caminhos = guardar_todas_imagens(imagens, asin, pasta="/tmp")

        caminho_telegram = caminhos.get("quadrada")
        sucesso = publicar_oferta(oferta, caminho_telegram) if caminho_telegram else False

        if sucesso:
            PASTA_SOCIAL = "imagens_sociais"
            os.makedirs(PASTA_SOCIAL, exist_ok=True)
            for formato in ["quadrada", "pinterest", "story"]:
                caminho_tmp = caminhos.get(formato)
                if caminho_tmp and os.path.exists(caminho_tmp):
                    destino = f"{PASTA_SOCIAL}/{asin}_{formato}.jpg"
                    with open(caminho_tmp, "rb") as f_in, open(destino, "wb") as f_out:
                        f_out.write(f_in.read())

            PASTA_META = "metadados_sociais"
            os.makedirs(PASTA_META, exist_ok=True)
            metadados = {
                "asin":             asin,
                "titulo":           oferta.get("titulo", ""),
                "preco":            oferta.get("preco", ""),
                "preco_anterior":   oferta.get("preco_anterior") or "",
                "desconto":         oferta.get("desconto", 0),
                "link":             oferta.get("link", ""),
                "tipo_deal":        tipo_deal,
                "deal_fim":         oferta.get("deal_fim", ""),
                "imagem_quadrada":  f"imagens_sociais/{asin}_quadrada.jpg",
                "imagem_pinterest": f"imagens_sociais/{asin}_pinterest.jpg",
                "imagem_story":     f"imagens_sociais/{asin}_story.jpg",
                "caracteristicas":  oferta.get("caracteristicas", []),
            }
            with open(f"{PASTA_META}/{asin}.json", "w", encoding="utf-8") as f:
                json.dump(metadados, f, ensure_ascii=False, indent=2)

            historico = registar_publicacao(asin, historico)
            guardar_publicado_txt(asin)
            publicadas_agora += 1

        for caminho in caminhos.values():
            try:
                os.remove(caminho)
            except OSError:
                pass

        if publicadas_agora < NUM_OFERTAS_POR_EXECUCAO:
            time.sleep(5)

    guardar_historico(historico)
    print(f"✅ {publicadas_agora} oferta(s) publicada(s).")


if __name__ == "__main__":
    main()
