# gerador_imagem.py
"""
Gera uma imagem 1080x1080 com:
 - Fundo branco
 - Foto do produto a ocupar toda a largura
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
BRANCO         = (255, 255, 255)
PRETO          = (20, 20, 25)
DOURADO_ESCURO = (200, 140, 0)     # dourado mais escuro para contraste no branco
CINZENTO_CLARO = (130, 130, 140)
CINZENTO_MEDIO = (150, 150, 160)
VERMELHO       = (220, 38, 38)
LINHA_SEP      = (230, 230, 235)

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

    canvas = Image.new("RGB", (LARGURA, ALTURA), BRANCO)
    draw = ImageDraw.Draw(canvas)

    # Área do produto — imagem a ocupar toda a largura
    AREA_PRODUTO_ALTURA = 620

    if url_imagem_produto:
        img_produto = _descarregar_imagem(url_imagem_produto)
        if img_produto:
            # Redimensiona para ocupar toda a largura, mantendo proporção,
            # e centra verticalmente dentro da área do produto
            img_produto = img_produto.convert("RGB")
            ratio = LARGURA / img_produto.width
            nova_largura = LARGURA
            nova_altura = int(img_produto.height * ratio)

            if nova_altura > AREA_PRODUTO_ALTURA:
                # Imagem muito alta — corta o excesso (mantém o centro)
                img_produto = img_produto.resize((nova_largura, nova_altura), Image.LANCZOS)
                excesso = nova_altura - AREA_PRODUTO_ALTURA
                img_produto = img_produto.crop((0, excesso // 2, nova_largura, excesso // 2 + AREA_PRODUTO_ALTURA))
                canvas.paste(img_produto, (0, 0))
            else:
                # Imagem mais pequena que a área — centra verticalmente
                img_produto = img_produto.resize((nova_largura, nova_altura), Image.LANCZOS)
                py = (AREA_PRODUTO_ALTURA - nova_altura) // 2
                canvas.paste(img_produto, (0, py))

    # Selo de desconto (sobreposto no canto superior direito da imagem)
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
              fill=LINHA_SEP, width=2)

    # Título do produto (até 3 linhas)
    fonte_titulo = _carregar_fonte(34, negrito=True)
    linhas = textwrap.wrap(titulo[:110], width=34)[:3]
    ty = AREA_PRODUTO_ALTURA + 28
    for linha in linhas:
        draw.text((60, ty), linha, font=fonte_titulo, fill=PRETO)
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
    draw.text((60, y_promo), preco_promo, font=fonte_promo, fill=DOURADO_ESCURO)

    # Rodapé
    altura_rodape = ALTURA - 80
    draw.rectangle([(0, altura_rodape - 10), (LARGURA, ALTURA)], fill=BRANCO)
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
