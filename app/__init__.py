import os
from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    """Application Factory Pattern - Estrutura Profissional"""
    
    app = Flask(
        __name__,
        template_folder=config_class.TEMPLATES_DIR,
        static_folder=config_class.STATIC_DIR
    )
    
    # Carrega as configurações
    app.config.from_object(config_class)
    
    # Cria pastas necessárias
    os.makedirs(app.config['DOWNLOADS_DIR'], exist_ok=True)
    os.makedirs(app.config['LOGS_DIR'], exist_ok=True)
    os.makedirs(app.config['PAYLOADS_DIR'], exist_ok=True)
    
    # ============================================
    # REGISTRO DOS BLUEPRINTS
    # ============================================
    from app.routes.main import main_bp
    from app.routes.captcha import captcha_bp
    from app.routes.fingerprint import fingerprint_bp
    from app.routes.hta import hta_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(captcha_bp)
    app.register_blueprint(fingerprint_bp)
    app.register_blueprint(hta_bp)
    
    return app