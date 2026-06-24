# gerador_imagem.py
import os
import io
import re
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont

# Cores
BRANCO         = (255, 255, 255)
PRETO          = (20, 20, 25)
DOURADO_ESCURO = (200, 140, 0)
CINZENTO_CLARO = (130, 130, 140)
CINZENTO_MEDIO = (150, 150, 160)
VERMELHO       = (220, 38, 38)
LINHA_SEP      = (230, 230, 235)


# ─────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────

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


def _remover_emojis(texto: str) -> str:
    """Remove emojis de uma string para evitar [] nas imagens."""
    return re.sub(
        r'[\U00010000-\U0010ffff\U0001F300-\U0001FAFF\U00002600-\U000027BF'
        r'\U0001FA00-\U0001FA9F\U00002702-\U000027B0\U0000FE00-\U0000FE0F]',
        '', texto, flags=re.UNICODE
    ).strip()


def _texto_riscado(draw, x, y, texto, fonte, cor):
    draw.text((x, y), texto, font=fonte, fill=cor)
    caixa = draw.textbbox((x, y), texto, font=fonte)
    meio_y = (caixa[1] + caixa[3]) // 2
    draw.line([(caixa[0], meio_y), (caixa[2], meio_y)], fill=cor, width=3)


def _colar_imagem_produto(canvas, img_produto, x, y, largura, altura):
    """
    Redimensiona a imagem do produto para caber na área definida
    SEM cortar — mantém proporções e centra na área.
    """
    img_produto = img_produto.convert("RGB")

    ratio_largura = largura / img_produto.width
    ratio_altura  = altura  / img_produto.height
    ratio         = min(ratio_largura, ratio_altura)

    nova_largura = int(img_produto.width  * ratio)
    nova_altura  = int(img_produto.height * ratio)

    img_produto = img_produto.resize((nova_largura, nova_altura), Image.LANCZOS)

    offset_x = x + (largura - nova_largura) // 2
    offset_y = y + (altura  - nova_altura)  // 2

    canvas.paste(img_produto, (offset_x, offset_y))


def _desenhar_badge(draw, cx, cy, raio, desconto_pct):
    """Desenha o círculo de desconto — só percentagem, centrada."""
    draw.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=VERMELHO)
    fonte = _carregar_fonte(int(raio * 0.52), negrito=True)

    texto = f"-{desconto_pct}%"
    caixa = draw.textbbox((0, 0), texto, font=fonte)
    texto_w = caixa[2] - caixa[0]
    texto_h = caixa[3] - caixa[1]
    draw.text(
        (cx - texto_w // 2, cy - texto_h // 2),
        texto, font=fonte, fill=BRANCO
    )

def _desenhar_rodape_simples(canvas, draw, y_inicio, largura, altura_total,
                              nome_canal, tamanho_fonte=28):
    """Rodapé com link do canal em vez do nome."""
    draw.rectangle([(0, y_inicio), (largura, altura_total)], fill=BRANCO)
    draw.line([(0, y_inicio), (largura, y_inicio)], fill=VERMELHO, width=3)

    fonte = _carregar_fonte(tamanho_fonte, negrito=True)
    texto = "t.me/poupamais_pt"
    caixa = draw.textbbox((0, 0), texto, font=fonte)
    draw.text(
        ((largura - (caixa[2]-caixa[0])) // 2, y_inicio + 8),
        texto, font=fonte, fill=CINZENTO_CLARO
    )


def _carregar_logo(tamanho: int = 80) -> Image.Image | None:
    """Carrega o logo do canal (logo.png na raiz do projecto)."""
    caminhos = [
        "logo.png",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
    ]
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                logo = Image.open(caminho).convert("RGBA")
                logo.thumbnail((tamanho, tamanho), Image.LANCZOS)
                return logo
            except Exception:
                pass
    return None


def _adicionar_logo(canvas: Image.Image, tamanho: int = 80,
                    margem: int = 20,
                    posicao: str = "inferior_esquerdo") -> Image.Image:
    """
    Sobrepõe o logo num canto da imagem.
    posicao: "inferior_esquerdo" | "inferior_direito" |
             "superior_esquerdo" | "superior_direito"
    """
    logo = _carregar_logo(tamanho)
    if not logo:
        return canvas

    W, H = canvas.size
    m = margem

    if posicao == "inferior_esquerdo":
        x, y = m, H - logo.height - m
    elif posicao == "inferior_direito":
        x, y = W - logo.width - m, H - logo.height - m
    elif posicao == "superior_esquerdo":
        x, y = m, m
    else:  # superior_direito
        x, y = W - logo.width - m, m

    # Fundo branco semi-transparente por trás do logo
    fundo = Image.new("RGBA", (logo.width + 16, logo.height + 16),
                      (255, 255, 255, 200))
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(fundo, (x - 8, y - 8), fundo)
    canvas_rgba.paste(logo, (x, y), logo)

    return canvas_rgba.convert("RGB")


# ─────────────────────────────────────────────
# FORMATO 1 — Telegram / Instagram Post
# 1080×1350px (4:5)
# ─────────────────────────────────────────────

def criar_imagem_quadrada(titulo, preco_anterior, preco_promo,
                          desconto_pct, url_imagem_produto,
                          nome_canal="Poupa Mais PT") -> Image.Image:

    W, H = 1080, 1080

    RODAPE_H    = 60
    PRECOS_H    = 130
    TITULO_H    = 110
    SEPARADOR_H = 15
    AREA_IMG_H  = H - RODAPE_H - PRECOS_H - TITULO_H - SEPARADOR_H

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    # Imagem do produto
    if url_imagem_produto:
        img = _descarregar_imagem(url_imagem_produto)
        if img:
            _colar_imagem_produto(canvas, img, 0, 0, W, AREA_IMG_H)

    # Badge de desconto
    if desconto_pct > 0:
        _desenhar_badge(draw, W - 90, 90, 60, desconto_pct)

    # Linha separadora
    SEP_Y = AREA_IMG_H + 8
    draw.line([(30, SEP_Y), (W - 30, SEP_Y)], fill=LINHA_SEP, width=2)

    # Título
    fonte_titulo = _carregar_fonte(30, negrito=True)
    linhas = textwrap.wrap(_remover_emojis(titulo)[:100], width=38)[:2]
    ty = SEP_Y + 12
    for linha in linhas:
        draw.text((50, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 40

    # Preços
    Y_PRECO = AREA_IMG_H + SEPARADOR_H + TITULO_H + 5
    if preco_anterior and desconto_pct > 0:
        _texto_riscado(draw, 50, Y_PRECO, preco_anterior,
                       _carregar_fonte(28), CINZENTO_MEDIO)
        y_promo = Y_PRECO + 42
    else:
        y_promo = Y_PRECO

    draw.text((50, y_promo), preco_promo,
              font=_carregar_fonte(72, negrito=True), fill=DOURADO_ESCURO)

    # Rodapé
    _desenhar_rodape_simples(canvas, draw, H - RODAPE_H, W, H,
                              nome_canal, tamanho_fonte=22)

    # Logo canto inferior direito
    canvas = _adicionar_logo(canvas, tamanho=70, margem=15,
                              posicao="inferior_direito")

    return canvas

# ─────────────────────────────────────────────
# FORMATO 2 — Pinterest
# 1000×1500px (2:3)
# ─────────────────────────────────────────────

def criar_imagem_pinterest(titulo, preco_anterior, preco_promo,
                           desconto_pct, url_imagem_produto,
                           nome_canal="Poupa Mais PT") -> Image.Image:

    W, H       = 1000, 1500
    AREA_IMG_H = 750

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    # Imagem do produto
    if url_imagem_produto:
        img = _descarregar_imagem(url_imagem_produto)
        if img:
            _colar_imagem_produto(canvas, img, 0, 0, W, AREA_IMG_H)

    # Badge de desconto
    if desconto_pct > 0:
        _desenhar_badge(draw, W - 100, 100, 68, desconto_pct)

    # Linha separadora
    draw.line([(30, AREA_IMG_H + 10), (W - 30, AREA_IMG_H + 10)],
              fill=LINHA_SEP, width=2)

    # Etiqueta "OFERTA"
    fonte_etiq = _carregar_fonte(26, negrito=True)
    draw.rectangle([(30, AREA_IMG_H + 25), (200, AREA_IMG_H + 65)],
                   fill=VERMELHO)
    draw.text((45, AREA_IMG_H + 30), "OFERTA",
              font=fonte_etiq, fill=BRANCO)

    # Título
    fonte_titulo = _carregar_fonte(38, negrito=True)
    linhas = textwrap.wrap(_remover_emojis(titulo)[:120], width=30)[:3]
    ty = AREA_IMG_H + 80
    for linha in linhas:
        draw.text((30, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 52

    # Preços
    Y_PRECO = 1130
    if preco_anterior and desconto_pct > 0:
        _texto_riscado(draw, 30, Y_PRECO, f"Antes: {preco_anterior}",
                       _carregar_fonte(36), CINZENTO_MEDIO)
        y_promo = Y_PRECO + 55
    else:
        y_promo = Y_PRECO

    draw.text((30, y_promo), preco_promo,
              font=_carregar_fonte(96, negrito=True), fill=DOURADO_ESCURO)

    # CTA
    fonte_cta = _carregar_fonte(30, negrito=True)
    draw.text((30, 1330), "Ver oferta completa:",
              font=fonte_cta, fill=PRETO)
    draw.text((30, 1375), "t.me/poupamais_pt",
              font=_carregar_fonte(30), fill=VERMELHO)

    # Rodapé
    _desenhar_rodape_simples(canvas, draw, H - 90, W, H,
                              nome_canal, tamanho_fonte=26)

    # Logo canto inferior esquerdo
    canvas = _adicionar_logo(canvas, tamanho=80, margem=20,
                              posicao="inferior_esquerdo")

    return canvas


# ─────────────────────────────────────────────
# FORMATO 3 — Stories Instagram/Facebook + TikTok
# 1080×1920px (9:16)
# ─────────────────────────────────────────────

def criar_imagem_story(titulo, preco_anterior, preco_promo,
                       desconto_pct, url_imagem_produto,
                       nome_canal="Poupa Mais PT") -> Image.Image:

    W, H       = 1080, 1920
    AREA_IMG_H = 900

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    # Cabeçalho vermelho
    draw.rectangle([(0, 0), (W, 110)], fill=VERMELHO)
    fonte_header = _carregar_fonte(46, negrito=True)
    texto_header = "OFERTA DO DIA"
    caixa_h = draw.textbbox((0, 0), texto_header, font=fonte_header)
    draw.text(
        ((W - (caixa_h[2]-caixa_h[0])) // 2, 28),
        texto_header, font=fonte_header, fill=BRANCO
    )

    # Imagem do produto
    if url_imagem_produto:
        img = _descarregar_imagem(url_imagem_produto)
        if img:
            _colar_imagem_produto(canvas, img, 0, 110, W, AREA_IMG_H)

    # Badge de desconto
    if desconto_pct > 0:
        _desenhar_badge(draw, W - 120, 230, 88, desconto_pct)

    # Linha separadora
    draw.line([(40, AREA_IMG_H + 120), (W - 40, AREA_IMG_H + 120)],
              fill=LINHA_SEP, width=2)

    # Título
    fonte_titulo = _carregar_fonte(44, negrito=True)
    linhas = textwrap.wrap(_remover_emojis(titulo)[:100], width=28)[:3]
    ty = AREA_IMG_H + 145
    for linha in linhas:
        draw.text((50, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 58

    # Preços
    Y_PRECO = 1430
    if preco_anterior and desconto_pct > 0:
        _texto_riscado(draw, 50, Y_PRECO, f"Antes: {preco_anterior}",
                       _carregar_fonte(42), CINZENTO_MEDIO)
        y_promo = Y_PRECO + 65
    else:
        y_promo = Y_PRECO

    draw.text((50, y_promo), preco_promo,
              font=_carregar_fonte(110, negrito=True), fill=DOURADO_ESCURO)

    # CTA
    draw.rectangle([(40, 1720), (W - 40, 1820)], fill=VERMELHO)
    fonte_cta = _carregar_fonte(42, negrito=True)
    cta_texto = "Link na bio  |  @poupamais_pt"
    caixa_cta = draw.textbbox((0, 0), cta_texto, font=fonte_cta)
    draw.text(
        ((W - (caixa_cta[2]-caixa_cta[0])) // 2, 1745),
        cta_texto, font=fonte_cta, fill=BRANCO
    )

    # Rodapé
    _desenhar_rodape_simples(canvas, draw, H - 90, W, H,
                              nome_canal, tamanho_fonte=28)

    # Logo canto superior esquerdo (bem visível, difícil de cortar)
    canvas = _adicionar_logo(canvas, tamanho=100, margem=25,
                              posicao="superior_esquerdo")

    return canvas


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — gera os 3 formatos de uma vez
# ─────────────────────────────────────────────

def criar_todas_imagens(titulo, preco_anterior, preco_promo,
                        desconto_pct, url_imagem_produto,
                        nome_canal="Poupa Mais PT") -> dict:
    """Gera os 3 formatos e devolve dicionário com os objectos Image."""
    return {
        "quadrada":  criar_imagem_quadrada(titulo, preco_anterior, preco_promo,
                                           desconto_pct, url_imagem_produto,
                                           nome_canal),
        "pinterest": criar_imagem_pinterest(titulo, preco_anterior, preco_promo,
                                            desconto_pct, url_imagem_produto,
                                            nome_canal),
        "story":     criar_imagem_story(titulo, preco_anterior, preco_promo,
                                        desconto_pct, url_imagem_produto,
                                        nome_canal),
    }


def guardar_imagem(canvas: Image.Image, asin: str,
                   pasta: str = "/tmp") -> str:
    """Guarda imagem quadrada — compatibilidade com código existente."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"oferta_{asin}.jpg")
    canvas.convert("RGB").save(caminho, "JPEG", quality=92)
    return caminho


def guardar_todas_imagens(imagens: dict, asin: str,
                          pasta: str = "/tmp") -> dict:
    """Guarda os 3 formatos em disco e devolve os caminhos."""
    os.makedirs(pasta, exist_ok=True)
    mapeamento = {
        "quadrada":  f"oferta_{asin}_quadrada.jpg",
        "pinterest": f"oferta_{asin}_pinterest.jpg",
        "story":     f"oferta_{asin}_story.jpg",
    }
    caminhos = {}
    for formato, nome_ficheiro in mapeamento.items():
        if formato in imagens:
            caminho = os.path.join(pasta, nome_ficheiro)
            imagens[formato].convert("RGB").save(caminho, "JPEG", quality=92)
            caminhos[formato] = caminho
            print(f"✅ Imagem gerada: {nome_ficheiro}")
    return caminhos
