from flask import abort
from flask_jwt_extended import get_jwt_identity

from .extensions import db


def current_user_id():
    # Tokens store the id as a string (the JWT spec requires `sub` to be a string).
    return int(get_jwt_identity())


def get_owned_or_404(model, obj_id):
    """Fetch a row that belongs to the logged-in user.

    Returns 404 when the row doesn't exist and 403 when it belongs to someone else.
    Every collection and deck route goes through this helper, so ownership is
    checked in exactly one place.
    """
    obj = db.session.get(model, obj_id)
    if obj is None:
        abort(404, description=f"{model.__name__} not found")
    if obj.user_id != current_user_id():
        abort(403, description="You don't have access to this item")
    return obj
