from flask import Flask
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import bcrypt, cors, db, jwt, migrate
from .scryfall import ScryfallError


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _check_secret(app)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401  (registers models with SQLAlchemy)
    from .routes import auth, cards, collection, decks

    for module in (auth, cards, collection, decks):
        app.register_blueprint(module.bp)

    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "scryfall_mode": app.config["SCRYFALL_MODE"]}

    return app


def _check_secret(app):
    secret = app.config.get("JWT_SECRET_KEY") or ""
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or shorter than 32 characters. "
            "Copy server/.env.example to server/.env and set a long random value, e.g. "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return {"error": "Please fix the highlighted fields", "fields": err.messages}, 400

    @app.errorhandler(ScryfallError)
    def handle_scryfall(err):
        return {"error": err.message}, err.status

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return {"error": err.description}, err.code

    # JWT problems all come back as 401 JSON so the React app can log the user out.
    @jwt.unauthorized_loader
    def missing_token(reason):
        return {"error": "Please log in", "detail": reason}, 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return {"error": "Your session is invalid. Please log in again.", "detail": reason}, 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return {"error": "Your session expired. Please log in again."}, 401
