# bot_telegram.py
"""
Formata e publica ofertas no canal de Telegram, em português de Portugal.
"""

import os
from telegram import Bot
from telegram import ParseMode
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CANAL_ID   = os.getenv("TELEGRAM_CHANNEL_ID")
NOME_CANAL = os.getenv("NOME_CANAL", "Casa & Cozinha PT 🏠")


def _etiqueta_desconto(pct: int) -> str:
    if pct >= 50: return "💥 PROMOÇÃO IMPERDÍVEL"
    if pct >= 35: return "🔥🔥🔥 MEGA DESCONTO"
    if pct >= 20: return "🔥🔥 GRANDE OFERTA"
    if pct >= 10: return "🔥 BOA OFERTA"
    return "✅ OFERTA"


def formatar_legenda(oferta: dict) -> str:
    """Cria a legenda (texto) que acompanha a imagem."""
    titulo          = oferta.get("titulo", "Produto Amazon")[:100]
    preco           = oferta.get("preco", "Ver preço")
    preco_anterior  = oferta.get("preco_anterior")
    desconto        = oferta.get("desconto", 0)
    link            = oferta.get("link", "")
    caracteristicas = oferta.get("caracteristicas", [])

    etiqueta = _etiqueta_desconto(desconto)

    linhas = [f"{etiqueta}\n", f"*{titulo}*\n"]

    # Pequena descrição do produto (características)
    if caracteristicas:
        linhas.append("📋 *Descrição:*")
        for c in caracteristicas:
            linhas.append(f"• {c[:90]}")
        linhas.append("")

    if preco_anterior and desconto > 0:
        linhas.append(f"~~De: {preco_anterior}~~")
        linhas.append(f"🏷️ *Por apenas: {preco}*")
        linhas.append(f"💰 Poupas {desconto}%\n")
    else:
        linhas.append(f"🏷️ *Preço: {preco}*\n")

    linhas.append(f"🛒 [Comprar na Amazon]({link})")
    linhas.append(
        "\n_Este canal contém links de afiliado da Amazon. "
        "Como Afiliado Amazon, recebo uma remuneração por compras "
        "que cumpram os requisitos aplicáveis._"
    )
    linhas.append("\n#oferta #amazon #casaecozinha #organização #portugal")

    return "\n".join(linhas)


def publicar_oferta(oferta: dict, caminho_imagem: str) -> bool:
    """Publica uma oferta (imagem + legenda) no canal."""
    bot = Bot(token=BOT_TOKEN)
    legenda = formatar_legenda(oferta)

    try:
        with open(caminho_imagem, "rb") as foto:
            bot.send_photo(
                chat_id=CANAL_ID,
                photo=foto,
                caption=legenda,
                parse_mode=ParseMode.MARKDOWN,
            )
        print(f"✅ Publicado: {oferta.get('titulo','')[:55]}")
        return True
    except TelegramError as e:
        print(f"❌ Erro ao publicar no Telegram: {e}")
        return False
