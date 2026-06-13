# importar_csv.py
import csv
import os
import re
from fila_manager import adicionar_produto, carregar_fila

FICHEIRO_CSV = "produtos_novos.csv"
CABECALHO    = ["titulo", "preco", "preco_anterior", "desconto",
                "imagem", "link", "caracteristica1", "caracteristica2", "caracteristica3"]


def formatar_preco(valor: str) -> str:
    valor = valor.strip().replace(",", ".")
    try:
        return f"{float(valor):.2f} €".replace(".", ",")
    except ValueError:
        return valor


def extrair_asin(link: str) -> str:
    padrao = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", link, re.IGNORECASE)
    if padrao:
        return padrao.group(1).upper()
    return "LINK" + str(abs(hash(link)) % 100000000)


def main():
    if not os.path.exists(FICHEIRO_CSV):
        print("⚠️ Ficheiro produtos_novos.csv não encontrado.")
        return

    fila_atual      = carregar_fila()
    asins_na_fila   = {p.get("asin") for p in fila_atual}
    adicionados     = 0
    ignorados       = 0

    with open(FICHEIRO_CSV, "r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            if not linha.get("titulo", "").strip():
                continue

            link = linha["link"].strip()
            asin = extrair_asin(link)

            if asin in asins_na_fila:
                print(f"⏭️  Ignorado (já na fila): {linha['titulo'][:50]}")
                ignorados += 1
                continue

            caracteristicas = []
            for i in range(1, 4):
                c = linha.get(f"caracteristica{i}", "").strip()
                if c:
                    caracteristicas.append(c)

            preco_anterior = linha.get("preco_anterior", "").strip()

            produto = {
                "asin":           asin,
                "titulo":         linha["titulo"].strip(),
                "preco":          formatar_preco(linha["preco"]),
                "preco_anterior": formatar_preco(preco_anterior) if preco_anterior else None,
                "desconto":       linha.get("desconto", "0").strip(),
                "imagem":         linha["imagem"].strip(),
                "link":           link,
                "caracteristicas": caracteristicas,
            }
            adicionar_produto(produto)
            asins_na_fila.add(asin)
            adicionados += 1
            print(f"✅ Adicionado [{asin}]: {produto['titulo'][:50]}")

    with open(FICHEIRO_CSV, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(CABECALHO)

    print(f"\n🎉 Adicionados: {adicionados} | Ignorados: {ignorados}. CSV limpo.")


if __name__ == "__main__":
    main()
