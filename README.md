# 🔴 Lab Red Team 2026

**Simulação Avançada de Phishing + Delivery de RAT com Rust Stager**

Projeto educacional para laboratório controlado de Red Team. Simula uma cadeia completa de ataque: **phishing → fingerprint → CAPTCHA → HTML Smuggling → HTA → Rust Stager in-memory**.

---

## ⚠️ AVISO LEGAL

Este projeto é **exclusivamente para fins educacionais** e testes em ambientes **totalmente controlados** (laboratório isolado, VMs autorizadas).  
Qualquer uso em redes de produção ou sem autorização expressa é **proibido** e pode configurar crime cibernético.

---

## ✨ Funcionalidades

- ✅ **CAPTCHA forte** gerado dinamicamente com PIL (distorção, ruído, rotação)
- ✅ **Browser Fingerprinting** + Anti-Bot / Anti-VM
- ✅ **HTML Smuggling** (HTA montado em memória via Blob)
- ✅ **Rust Stager** moderno (in-memory execution + XOR decryption)
- ✅ Anti-análise (VM detection, timing, hardware check)
- ✅ Logging completo de acessos e ações
- ✅ Masquerading (arquivos com nome legítimo: `vlc-media-updater.exe`)
- ✅ Multi-stage delivery (HTA → Rust Stager → Shellcode)

---

## 📍 Fluxo Completo do Ataque

1. **Acesso inicial** → `fp_page.html` coleta fingerprint
2. **Verificação** → `index.html` com CAPTCHA
3. **Engenharia Social** → `success.html` com progress bar fake
4. **Delivery** → HTA gerado via Smuggling
5. **Execução** → Rust Stager baixa e executa shellcode **in-memory**
6. **Persistência** → Shellcode (calc.exe ou beacon real)

---

## 🚀 Como Rodar (Ambiente Controlado)

### Pré-requisitos
- Python 3.10+
- Rust + Cargo (instalado)
- MSYS2 MinGW x64 (para compilar o Rust Stager)

### 1. Instalar dependências Python
```bash
pip install -r requirements.txt