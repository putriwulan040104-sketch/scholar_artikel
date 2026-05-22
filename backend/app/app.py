from flask import Flask
from flask_cors import CORS
from app.routes.publication import publication_bp
from app.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    
    # Izinkan React akses Flask
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    app.register_blueprint(publication_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    return app