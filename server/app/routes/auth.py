from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import func

from ..extensions import db, limiter
from ..models import User
from ..schemas import LoginSchema, SignupSchema
from ..utils import current_user_id

bp = Blueprint("auth", __name__, url_prefix="/api")


def _auth_limit():
    return current_app.config["AUTH_RATE_LIMIT"]


def _token_response(user, status=200):
    token = create_access_token(identity=str(user.id))
    return {"token": token, "user": user.to_dict()}, status


@bp.post("/signup")
@limiter.limit(_auth_limit)
def signup():
    data = SignupSchema().load(request.get_json(silent=True) or {})
    username = data["username"].strip()
    email = data["email"].strip().lower()

    errors = {}
    if User.query.filter(func.lower(User.username) == username.lower()).first():
        errors["username"] = ["That username is taken."]
    if User.query.filter_by(email=email).first():
        errors["email"] = ["An account with that email already exists."]
    if errors:
        return {"error": "Signup failed", "fields": errors}, 409

    user = User(username=username, email=email)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return _token_response(user, 201)


@bp.post("/login")
@limiter.limit(_auth_limit)
def login():
    data = LoginSchema().load(request.get_json(silent=True) or {})
    ident = data["username"].strip()
    user = User.query.filter(
        (func.lower(User.username) == ident.lower()) | (User.email == ident.lower())
    ).first()
    # Same message either way so the API doesn't reveal which usernames exist.
    if user is None or not user.check_password(data["password"]):
        return {"error": "Incorrect username or password"}, 401
    return _token_response(user)


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, current_user_id())
    if user is None:
        return {"error": "User no longer exists"}, 401
    return {
        "user": user.to_dict(),
        "stats": {
            "unique_cards": len(user.collection_items),
            "total_cards": sum(ci.quantity for ci in user.collection_items),
            "decks": len(user.decks),
        },
    }
