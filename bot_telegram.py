# bot_telegram.py
import os
from telegram import Bot, ParseMode
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN")
CANAL_ID         = os.getenv("TELEGRAM_CHANNEL_ID")
NOME_CANAL       = os.getenv("NOME_CANAL", "Poupa Mais PT")
PRIME_LINK       = os.getenv("AMAZON_PRIME_LINK", "https://www.amazon.es/prime")


def _etiqueta_desconto(pct: int) -> str:
    if pct >= 50: return "💥 PROMOÇÃO IMPERDÍVEL"
    if pct >= 35: return "🔥🔥🔥 MEGA DESCONTO"
    if pct >= 20: return "🔥🔥 GRANDE OFERTA"
    if pct >= 10: return "🔥 BOA OFERTA"
    return "✅ OFERTA"


def formatar_legenda(oferta: dict) -> str:
    titulo          = oferta.get("titulo", "Produto Amazon")[:100]
    preco           = oferta.get("preco", "Ver preço")
    preco_anterior  = oferta.get("preco_anterior")
    desconto        = int(oferta.get("desconto", 0))
    link            = oferta.get("link", "")
    caracteristicas = oferta.get("caracteristicas", [])

    etiqueta = _etiqueta_desconto(desconto)
    linhas = [f"{etiqueta}\n", f"*{titulo}*\n"]

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
        f"\n📦 *Tens Amazon Prime?*\n"
        f"Entrega rápida e gratuita neste e em milhões de produtos.\n"
        f"[Experimenta grátis 30 dias]({PRIME_LINK})"
    )

    linhas.append("\n\n_#ad — links de afiliado Amazon_")
    linhas.append("\n#oferta #amazon #descontos #promoções #portugal")

    return "\n".join(linhas)


def publicar_oferta(oferta: dict, caminho_imagem: str) -> bool:
    bot     = Bot(token=BOT_TOKEN)
    legenda = formatar_legenda(oferta)
    try:
        with open(caminho_imagem, "rb") as foto:
            bot.send_photo(
                chat_id    = CANAL_ID,
                photo      = foto,
                caption    = legenda,
                parse_mode = ParseMode.MARKDOWN,
            )
        print(f"✅ Publicado: {oferta.get('titulo','')[:55]}")
        return True
    except TelegramError as e:
        print(f"Erro Telegram: {e}")
        return False
