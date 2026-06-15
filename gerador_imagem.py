# gerador_imagem.py
import os
import io
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


def _colar_imagem_produto(canvas, img_produto, x, y, largura, altura):
    """Redimensiona e cola imagem do produto numa área definida."""
    img_produto = img_produto.convert("RGB")
    ratio = largura / img_produto.width
    nova_largura = largura
    nova_altura = int(img_produto.height * ratio)

    if nova_altura > altura:
        img_produto = img_produto.resize((nova_largura, nova_altura), Image.LANCZOS)
        excesso = nova_altura - altura
        img_produto = img_produto.crop((0, excesso // 2, nova_largura, excesso // 2 + altura))
    else:
        img_produto = img_produto.resize((nova_largura, nova_altura), Image.LANCZOS)
        y = y + (altura - nova_altura) // 2

    canvas.paste(img_produto, (x, y))


def _desenhar_badge(draw, cx, cy, raio, desconto_pct):
    """Desenha o círculo de desconto."""
    draw.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=VERMELHO)
    fonte_grande  = _carregar_fonte(int(raio * 0.44), negrito=True)
    fonte_pequena = _carregar_fonte(int(raio * 0.25), negrito=True)

    texto_pct = f"-{desconto_pct}%"
    caixa = draw.textbbox((0, 0), texto_pct, font=fonte_grande)
    draw.text(
        (cx - (caixa[2]-caixa[0])//2, cy - (caixa[3]-caixa[1])//2 - int(raio*0.1)),
        texto_pct, font=fonte_grande, fill=BRANCO
    )
    texto_poupa = "POUPA"
    caixa2 = draw.textbbox((0, 0), texto_poupa, font=fonte_pequena)
    draw.text(
        (cx - (caixa2[2]-caixa2[0])//2, cy + int(raio * 0.36)),
        texto_poupa, font=fonte_pequena, fill=BRANCO
    )


def _desenhar_rodape(canvas, draw, y_inicio, largura, altura_total, nome_canal, tamanho_fonte=28):
    """Desenha o rodapé vermelho com nome do canal."""
    draw.rectangle([(0, y_inicio), (largura, altura_total)], fill=BRANCO)
    draw.line([(0, y_inicio), (largura, y_inicio)], fill=VERMELHO, width=3)
    fonte = _carregar_fonte(tamanho_fonte, negrito=True)
    texto = f"🛒  {nome_canal}  |  Amazon.es"
    caixa = draw.textbbox((0, 0), texto, font=fonte)
    draw.text(
        ((largura - (caixa[2]-caixa[0])) // 2, y_inicio + 8),
        texto, font=fonte, fill=CINZENTO_CLARO
    )


# ─────────────────────────────────────────────
# FORMATO 1 — Telegram / Instagram Post
# 1080×1080px (quadrado)
# ─────────────────────────────────────────────
def criar_imagem_quadrada(titulo, preco_anterior, preco_promo,
                          desconto_pct, url_imagem_produto,
                          nome_canal="Poupa Mais PT 🇵🇹") -> Image.Image:

    W, H = 1080, 1080
    AREA_IMG_H = 620

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    if url_imagem_produto:
        img = _descarregar_imagem(url_imagem_produto)
        if img:
            _colar_imagem_produto(canvas, img, 0, 0, W, AREA_IMG_H)

    if desconto_pct > 0:
        _desenhar_badge(draw, W - 112, 112, 72, desconto_pct)

    draw.line([(40, AREA_IMG_H + 10), (W - 40, AREA_IMG_H + 10)],
              fill=LINHA_SEP, width=2)

    fonte_titulo = _carregar_fonte(34, negrito=True)
    linhas = textwrap.wrap(titulo[:110], width=34)[:3]
    ty = AREA_IMG_H + 28
    for linha in linhas:
        draw.text((60, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 44

    Y_PRECO = 810
    if preco_anterior and desconto_pct > 0:
        _texto_riscado(draw, 60, Y_PRECO, preco_anterior,
                       _carregar_fonte(34), CINZENTO_MEDIO)
        y_promo = Y_PRECO + 50
    else:
        y_promo = Y_PRECO

    draw.text((60, y_promo), preco_promo,
              font=_carregar_fonte(88, negrito=True), fill=DOURADO_ESCURO)

    _desenhar_rodape(canvas, draw, H - 80, W, H, nome_canal, tamanho_fonte=28)

    return canvas


# ─────────────────────────────────────────────
# FORMATO 2 — Pinterest
# 1000×1500px (2:3 vertical)
# ─────────────────────────────────────────────
def criar_imagem_pinterest(titulo, preco_anterior, preco_promo,
                           desconto_pct, url_imagem_produto,
                           nome_canal="Poupa Mais PT 🇵🇹") -> Image.Image:

    W, H = 1000, 1500
    AREA_IMG_H = 750

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    if url_imagem_produto:
        img = _descarregar_imagem(url_imagem_produto)
        if img:
            _colar_imagem_produto(canvas, img, 0, 0, W, AREA_IMG_H)

    if desconto_pct > 0:
        _desenhar_badge(draw, W - 100, 100, 68, desconto_pct)

    draw.line([(30, AREA_IMG_H + 10), (W - 30, AREA_IMG_H + 10)],
              fill=LINHA_SEP, width=2)

    # Etiqueta categoria
    fonte_etiq  = _carregar_fonte(26, negrito=True)
    draw.rectangle([(30, AREA_IMG_H + 25), (200, AREA_IMG_H + 65)], fill=VERMELHO)
    draw.text((45, AREA_IMG_H + 30), "OFERTA", font=fonte_etiq, fill=BRANCO)

    fonte_titulo = _carregar_fonte(38, negrito=True)
    linhas = textwrap.wrap(titulo[:120], width=30)[:3]
    ty = AREA_IMG_H + 80
    for linha in linhas:
        draw.text((30, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 52

    # Preços
    Y_PRECO = 1130
    if preco_anterior and desconto_pct > 0:
        fonte_ant = _carregar_fonte(36)
        _texto_riscado(draw, 30, Y_PRECO, f"Antes: {preco_anterior}",
                       fonte_ant, CINZENTO_MEDIO)
        y_promo = Y_PRECO + 55
    else:
        y_promo = Y_PRECO

    draw.text((30, y_promo), preco_promo,
              font=_carregar_fonte(96, negrito=True), fill=DOURADO_ESCURO)

    # CTA
    fonte_cta = _carregar_fonte(30, negrito=True)
    draw.text((30, 1330), "👉 Ver oferta completa:",
              font=fonte_cta, fill=PRETO)
    draw.text((30, 1375), "t.me/poupamais_pt",
              font=_carregar_fonte(30), fill=VERMELHO)

    _desenhar_rodape(canvas, draw, H - 90, W, H, nome_canal, tamanho_fonte=26)

    return canvas


# ─────────────────────────────────────────────
# FORMATO 3 — Stories Instagram/Facebook + TikTok
# 1080×1920px (9:16 vertical)
# ─────────────────────────────────────────────
def criar_imagem_story(titulo, preco_anterior, preco_promo,
                       desconto_pct, url_imagem_produto,
                       nome_canal="Poupa Mais PT 🇵🇹") -> Image.Image:

    W, H = 1080, 1920
    AREA_IMG_H = 900

    canvas = Image.new("RGB", (W, H), BRANCO)
    draw   = ImageDraw.Draw(canvas)

    # Cabeçalho vermelho
    draw.rectangle([(0, 0), (W, 110)], fill=VERMELHO)
    fonte_header = _carregar_fonte(46, negrito=True)
    texto_header = "🔥 OFERTA DO DIA"
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

    if desconto_pct > 0:
        _desenhar_badge(draw, W - 120, 230, 88, desconto_pct)

    draw.line([(40, AREA_IMG_H + 120), (W - 40, AREA_IMG_H + 120)],
              fill=LINHA_SEP, width=2)

    # Título
    fonte_titulo = _carregar_fonte(44, negrito=True)
    linhas = textwrap.wrap(titulo[:100], width=28)[:3]
    ty = AREA_IMG_H + 145
    for linha in linhas:
        draw.text((50, ty), linha, font=fonte_titulo, fill=PRETO)
        ty += 58

    # Preços
    Y_PRECO = 1430
    if preco_anterior and desconto_pct > 0:
        fonte_ant = _carregar_fonte(42)
        _texto_riscado(draw, 50, Y_PRECO, f"Antes: {preco_anterior}",
                       fonte_ant, CINZENTO_MEDIO)
        y_promo = Y_PRECO + 65
    else:
        y_promo = Y_PRECO

    draw.text((50, y_promo), preco_promo,
              font=_carregar_fonte(110, negrito=True), fill=DOURADO_ESCURO)

    # CTA
    draw.rectangle([(40, 1720), (W - 40, 1820)], fill=VERMELHO)
    fonte_cta = _carregar_fonte(42, negrito=True)
    cta_texto = "👆 Link na bio  |  @poupamais_pt"
    caixa_cta = draw.textbbox((0, 0), cta_texto, font=fonte_cta)
    draw.text(
        ((W - (caixa_cta[2]-caixa_cta[0])) // 2, 1745),
        cta_texto, font=fonte_cta, fill=BRANCO
    )

    _desenhar_rodape(canvas, draw, H - 90, W, H, nome_canal, tamanho_fonte=28)

    return canvas


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — gera os 3 formatos de uma vez
# ─────────────────────────────────────────────
def criar_todas_imagens(titulo, preco_anterior, preco_promo,
                        desconto_pct, url_imagem_produto,
                        nome_canal="Poupa Mais PT 🇵🇹") -> dict:
    """
    Gera os 3 formatos e devolve dicionário com os objectos Image.
    """
    return {
        "quadrada":  criar_imagem_quadrada(titulo, preco_anterior, preco_promo,
                                           desconto_pct, url_imagem_produto, nome_canal),
        "pinterest": criar_imagem_pinterest(titulo, preco_anterior, preco_promo,
                                            desconto_pct, url_imagem_produto, nome_canal),
        "story":     criar_imagem_story(titulo, preco_anterior, preco_promo,
                                        desconto_pct, url_imagem_produto, nome_canal),
    }


def guardar_imagem(canvas: Image.Image, asin: str, pasta: str = "/tmp") -> str:
    """Guarda imagem quadrada (Telegram) — compatibilidade com código existente."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"oferta_{asin}.jpg")
    canvas.convert("RGB").save(caminho, "JPEG", quality=92)
    return caminho


def guardar_todas_imagens(imagens: dict, asin: str, pasta: str = "/tmp") -> dict:
    """
    Guarda os 3 formatos em disco.
    Devolve dicionário com os caminhos de cada ficheiro.
    """
    os.makedirs(pasta, exist_ok=True)
    caminhos = {}
    mapeamento = {
        "quadrada":  f"oferta_{asin}_quadrada.jpg",
        "pinterest": f"oferta_{asin}_pinterest.jpg",
        "story":     f"oferta_{asin}_story.jpg",
    }
    for formato, nome_ficheiro in mapeamento.items():
        if formato in imagens:
            caminho = os.path.join(pasta, nome_ficheiro)
            imagens[formato].convert("RGB").save(caminho, "JPEG", quality=92)
            caminhos[formato] = caminho
            print(f"✅ Imagem gerada: {nome_ficheiro}")

    return caminhos
