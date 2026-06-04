// ========================================================
// Fingerprinting Avançado - Lab Red Team 2026
// ========================================================

async function coletarFingerprint() {
    const fingerprint = {};

    // === 1. Informações básicas ===
    fingerprint.userAgent = navigator.userAgent;
    fingerprint.language = navigator.language;
    fingerprint.languages = navigator.languages;
    fingerprint.platform = navigator.platform;
    fingerprint.hardwareConcurrency = navigator.hardwareConcurrency;
    fingerprint.deviceMemory = navigator.deviceMemory || "unknown";
    fingerprint.doNotTrack = navigator.doNotTrack;
    fingerprint.cookieEnabled = navigator.cookieEnabled;

    // === 2. Tela ===
    fingerprint.screen = {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth,
        pixelDepth: screen.pixelDepth
    };

    // === 3. Timezone ===
    fingerprint.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    fingerprint.timezoneOffset = new Date().getTimezoneOffset();

    // === 4. Canvas Fingerprint (muito poderoso) ===
    try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        ctx.textBaseline = "top";
        ctx.font = "14px Arial";
        ctx.fillStyle = "#f60";
        ctx.fillRect(125, 1, 62, 20);
        ctx.fillStyle = "#069";
        ctx.fillText("Fingerprint LabRT 2026", 2, 15);
        ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
        ctx.fillText("Fingerprint LabRT 2026", 4, 17);
        fingerprint.canvas = canvas.toDataURL();
    } catch (e) {
        fingerprint.canvas = "error";
    }

    // === 5. WebGL Fingerprint ===
    try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (gl) {
            fingerprint.webgl = {
                vendor: gl.getParameter(gl.VENDOR),
                renderer: gl.getParameter(gl.RENDERER),
                version: gl.getParameter(gl.VERSION)
            };
        }
    } catch (e) {
        fingerprint.webgl = "error";
    }

    // === 6. AudioContext Fingerprint ===
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        fingerprint.audio = {
            sampleRate: audioCtx.sampleRate,
            maxChannelCount: audioCtx.destination.maxChannelCount
        };
    } catch (e) {
        fingerprint.audio = "error";
    }

    // === 7. Plugins ===
    fingerprint.plugins = [];
    for (let i = 0; i < navigator.plugins.length; i++) {
        fingerprint.plugins.push(navigator.plugins[i].name);
    }

    return fingerprint;
}

// Envia o fingerprint para o servidor
async function enviarFingerprint() {
    try {
        const dados = await coletarFingerprint();
        await fetch("/fingerprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });
        console.log("[+] Fingerprint enviado com sucesso");
    } catch (e) {
        console.log("[!] Erro ao enviar fingerprint");
    }
}

// Executa automaticamente quando a página carrega
window.addEventListener("load", () => {
    enviarFingerprint();
});