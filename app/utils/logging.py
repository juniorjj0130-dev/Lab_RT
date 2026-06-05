import os
from datetime import datetime
from flask import request

def log_event(mensagem: str, victim_id: str = None, level: str = "INFO"):
    """
    Função centralizada de logging.
    level: INFO, WARNING, ERROR, SUCCESS
    """
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    victim = f" | Victim: {victim_id}" if victim_id else ""
    log_line = f"[{timestamp}] [{level}] {ip} | {ua}{victim} | {mensagem}\n"
    
    # Caminho do log (vem do config)
    from flask import current_app
    log_path = os.path.join(current_app.config['LOGS_DIR'], "access.log")
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_line)
    
    # Também imprime no console (útil durante desenvolvimento)
    print(log_line.strip())