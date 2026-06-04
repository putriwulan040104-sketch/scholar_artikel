from flask import Flask
from flask_cors import CORS

from app.routes.auth import auth_bp
from app.routes.publication import publication_bp
from app.routes.search import search_bp
from app.routes.request import request_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # register semua blueprint di sini
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(publication_bp, url_prefix="/api")
    app.register_blueprint(search_bp, url_prefix="/api")
    app.register_blueprint(request_bp, url_prefix="/api")

    return app
