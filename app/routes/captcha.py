from flask import Blueprint, render_template, request, session, redirect, url_for, send_file, abort, current_app
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import random
import uuid
import time
import hmac
from functools import wraps
from app.utils.logging import log_event

captcha_bp = Blueprint('captcha', __name__)


def gerar_captcha(dificuldade: str = "medio"):
    """Gera CAPTCHA com distorção, ruído e rotação"""
    largura, altura = 460, 170
    img = Image.new("RGB", (largura, altura), "#0d1117")
    draw = ImageDraw.Draw(img)

    # Ruído de fundo
    for _ in range(1100):
        x = random.randint(0, largura - 1)
        y = random.randint(0, altura - 1)
        draw.point((x, y), fill=(random.randint(25, 70),) * 3)

    # Grid
    for x in range(0, largura, 28):
        draw.line([(x, 0), (x, altura)], fill="#23272f", width=1)
    for y in range(0, altura, 28):
        draw.line([(0, y), (largura, y)], fill="#23272f", width=1)

    # Texto
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    if dificuldade == "dificil":
        chars += "abcdefghjkmnpqrstuvwxyz"

    tamanho = 6 if dificuldade != "facil" else 5
    codigo = ''.join(random.choices(chars, k=tamanho))

    x_pos = 35
    for letra in codigo:
        try:
            font = ImageFont.truetype(
                os.path.join(current_app.config['BASE_DIR'], "static/fonts/arialbd.ttf"),
                random.randint(52, 68)
            )
        except:
            font = ImageFont.load_default()

        cor = (
            random.randint(140, 255),
            random.randint(140, 255),
            random.randint(200, 255)
        )
        angulo = random.randint(-28, 28)

        temp = Image.new("RGBA", (90, 110), (0, 0, 0, 0))
        d = ImageDraw.Draw(temp)
        d.text((15, 12), letra, font=font, fill=cor)
        rotacionada = temp.rotate(angulo, expand=True, resample=Image.BICUBIC)
        img.paste(rotacionada, (x_pos + random.randint(-8, 8), random.randint(32, 55)), rotacionada)
        x_pos += random.randint(52, 68)

    # Linhas de interferência
    for _ in range(7):
        x1, y1 = random.randint(10, 120), random.randint(10, 160)
        x2, y2 = random.randint(320, 450), random.randint(10, 160)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(70, 160), random.randint(90, 200), 255), width=2)

    img = img.filter(ImageFilter.SMOOTH_MORE)

    nome_arquivo = f"captcha_{uuid.uuid4().hex[:10]}.png"
    caminho = os.path.join(current_app.config['DOWNLOADS_DIR'], nome_arquivo)
    img.save(caminho, "PNG")

    session["captcha_codigo"] = codigo
    session["captcha_arquivo"] = nome_arquivo
    session["captcha_criado_em"] = time.time()

    return codigo, nome_arquivo


def validar_captcha(entrada_usuario: str) -> bool:
    """Valida o CAPTCHA com expiração"""
    if "captcha_codigo" not in session or "captcha_criado_em" not in session:
        return False
    if time.time() - session["captcha_criado_em"] > current_app.config.get('CAPTCHA_EXPIRATION_SECONDS', 300):
        return False
    return hmac.compare_digest(entrada_usuario.upper().strip(), session.get("captcha_codigo", ""))


def require_captcha(f):
    """Decorator para proteger rotas que exigem CAPTCHA validado"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        if ip not in current_app.config.get('IP_VALIDADO', {}):
            log_event("BLOQUEADO - CAPTCHA NÃO VALIDADO")
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return wrapper


@captcha_bp.route('/c/<nome>')
def serve_captcha(nome):
    """Serve a imagem do CAPTCHA"""
    caminho = os.path.join(current_app.config['DOWNLOADS_DIR'], nome)
    if os.path.exists(caminho):
        return send_file(caminho, mimetype="image/png")
    abort(404)