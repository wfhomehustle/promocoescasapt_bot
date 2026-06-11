# gerador_imagem.py
"""
Gera uma imagem 1080x1080 com:
 - Foto do produto
 - Preço anterior riscado, em letra pequena
 - Preço promocional, em letra grande
 - Selo de desconto
"""

import os
import io
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont

# Cores
FUNDO_ESCURO   = (15, 15, 20)
CARTAO_FUNDO   = (26, 26, 36)
DOURADO        = (250, 185, 11)
CINZENTO_CLARO = (180, 180, 190)
CINZENTO_MEDIO = (110, 110, 125)
VERMELHO       = (220, 38, 38)
BRANCO         = (255, 255, 255)

LARGURA, ALTURA = 1080, 1080


def _descarregar_imagem(url: str):
    try:
        url = url.strip().replace(" ", "%20")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"⚠️ Não foi possível descarregar a imagem: {e}")
        return None


def _carregar_fonte(tamanho: int, negrito: bool = False):
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if negrito
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for caminho in candidatos:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except Exception:
                pass
    return ImageFont.load_default()


def _texto_riscado(draw, x, y, texto, fonte, cor):
    draw.text((x, y), texto, font=fonte, fill=cor)
    caixa = draw.textbbox((x, y), texto, font=fonte)
    meio_y = (caixa[1] + caixa[3]) // 2
    draw.line([(caixa[0], meio_y), (caixa[2], meio_y)], fill=cor, width=3)


def criar_imagem_oferta(titulo: str,
                        preco_anterior: str | None,
                        preco_promo: str,
                        desconto_pct: int,
                        url_imagem_produto: str | None,
                        nome_canal: str = "Casa & Cozinha PT 🏠") -> Image.Image:

    canvas = Image.new("RGB", (LARGURA, ALTURA), FUNDO_ESCURO)
    draw = ImageDraw.Draw(canvas)

    # Área do produto
    AREA_PRODUTO_ALTURA = 580
    draw.rounded_rectangle(
        (40, 40, LARGURA - 40, AREA_PRODUTO_ALTURA),
        radius=24, fill=CARTAO_FUNDO
    )

    # Imagem do produto centrada
    if url_imagem_produto:
        img_produto = _descarregar_imagem(url_imagem_produto)
        if img_produto:
            img_produto.thumbnail((460, 460), Image.LANCZOS)
            fundo_branco = Image.new("RGBA", img_produto.size, (255, 255, 255, 230))
            combinado = Image.alpha_composite(fundo_branco, img_produto).convert("RGB")
            px = (LARGURA - combinado.width) // 2
            py = 60 + (460 - combinado.height) // 2
            canvas.paste(combinado, (px, py))

    # Selo de desconto
    if desconto_pct > 0:
        raio = 72
        cx, cy = LARGURA - 40 - raio, 40 + raio
        draw.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=VERMELHO)
        fonte_grande = _carregar_fonte(32, negrito=True)
        fonte_pequena = _carregar_fonte(18, negrito=True)

        texto_pct = f"-{desconto_pct}%"
        caixa = draw.textbbox((0, 0), texto_pct, font=fonte_grande)
        draw.text((cx - (caixa[2]-caixa[0])//2, cy - (caixa[3]-caixa[1])//2 - 8),
                  texto_pct, font=fonte_grande, fill=BRANCO)

        texto_poupa = "POUPA"
        caixa2 = draw.textbbox((0, 0), texto_poupa, font=fonte_pequena)
        draw.text((cx - (caixa2[2]-caixa2[0])//2, cy + 26),
                  texto_poupa, font=fonte_pequena, fill=BRANCO)

    # Linha separadora
    draw.line([(40, AREA_PRODUTO_ALTURA + 10), (LARGURA - 40, AREA_PRODUTO_ALTURA + 10)],
              fill=(50, 50, 65), width=2)

    # Título do produto (até 3 linhas)
    fonte_titulo = _carregar_fonte(34, negrito=True)
    linhas = textwrap.wrap(titulo[:110], width=34)[:3]
    ty = AREA_PRODUTO_ALTURA + 28
    for linha in linhas:
        draw.text((60, ty), linha, font=fonte_titulo, fill=BRANCO)
        ty += 44

    # Preços
    Y_PRECO = 810

    if preco_anterior and desconto_pct > 0:
        fonte_anterior = _carregar_fonte(34, negrito=False)  # letra pequena
        _texto_riscado(draw, 60, Y_PRECO, preco_anterior, fonte_anterior, CINZENTO_MEDIO)
        y_promo = Y_PRECO + 50
    else:
        y_promo = Y_PRECO

    fonte_promo = _carregar_fonte(88, negrito=True)  # letra grande
    draw.text((60, y_promo), preco_promo, font=fonte_promo, fill=DOURADO)

    # Rodapé
    altura_rodape = ALTURA - 80
    draw.rectangle([(0, altura_rodape - 10), (LARGURA, ALTURA)], fill=(10, 10, 15))
    draw.line([(0, altura_rodape - 10), (LARGURA, altura_rodape - 10)], fill=VERMELHO, width=3)

    fonte_rodape = _carregar_fonte(28, negrito=True)
    texto_rodape = f"🛒  {nome_canal}  |  Amazon.es"
    caixa_rod = draw.textbbox((0, 0), texto_rodape, font=fonte_rodape)
    draw.text(((LARGURA - (caixa_rod[2]-caixa_rod[0])) // 2, altura_rodape + 4),
              texto_rodape, font=fonte_rodape, fill=CINZENTO_CLARO)

    return canvas


def guardar_imagem(canvas: Image.Image, asin: str, pasta: str = "/tmp") -> str:
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"oferta_{asin}.jpg")
    canvas.convert("RGB").save(caminho, "JPEG", quality=92)
    return caminho
