from flask import Flask
from flask_cors import CORS
from app.routes.auth import auth_bp
from app.routes.publication import publication_bp

def create_app():
  app = Flask(__name__)
  CORS(app)

  @app.route("/")
  def home():
    return "Backend API running"
  
  app.register_blueprint(auth_bp, url_prefix="/api/auth")
  
  app.register_blueprint(
        publication_bp,
        url_prefix="/api/publications"
    )

  return app