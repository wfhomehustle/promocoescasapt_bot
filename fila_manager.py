# fila_manager.py
import json
import os

FICHEIRO_FILA = "produtos_fila.json"


def carregar_fila() -> list:
    if not os.path.exists(FICHEIRO_FILA):
        return []
    with open(FICHEIRO_FILA, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_fila(fila: list) -> None:
    with open(FICHEIRO_FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)


def adicionar_produto(produto: dict) -> None:
    fila = carregar_fila()
    fila.append(produto)
    guardar_fila(fila)


def retirar_proximo() -> dict | None:
    fila = carregar_fila()
    if not fila:
        return None
    produto = fila.pop(0)
    guardar_fila(fila)
    return produto
