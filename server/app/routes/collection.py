from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from ..extensions import db
from ..models import Card, CollectionItem
from ..schemas import CollectionAddSchema, CollectionQuerySchema, CollectionUpdateSchema
from ..scryfall import get_card
from ..utils import current_user_id, get_owned_or_404

bp = Blueprint("collection", __name__, url_prefix="/api/collection")


SORTS = {
    "name": (Card.name.asc(),),
    "price": (Card.price_usd.desc().nulls_last(), Card.name.asc()),
    "quantity": (CollectionItem.quantity.desc(), Card.name.asc()),
    "recent": (CollectionItem.added_at.desc(), CollectionItem.id.desc()),
}


def _apply_filters(query, params):
    if params["q"]:
        query = query.filter(Card.name.ilike(f"%{params['q']}%"))
    color = params.get("color")
    if color == "C":  # colorless
        query = query.filter(Card.colors == "[]")
    elif color == "M":  # multicolored: more than one colour in the JSON list
        query = query.filter(Card.colors.like('%,%'))
    elif color:
        query = query.filter(Card.colors.like(f'%"{color}"%'))
    return query


@bp.get("")
@jwt_required()
def index():
    """List the user's collection with optional filtering, sorting and pagination.

    Query params: q (name contains), color (W U B R G, C colorless, M multicolor),
    sort (name | price | quantity | recent), page, per_page (max 100).
    """
    params = CollectionQuerySchema().load(request.args)
    base = CollectionItem.query.join(Card).filter(CollectionItem.user_id == current_user_id())

    filtered = _apply_filters(base, params).order_by(*SORTS[params["sort"]])
    page = filtered.paginate(page=params["page"], per_page=params["per_page"], error_out=False)

    # Stats always describe the whole collection, not just the current filter.
    unique, total, value = (
        base.with_entities(
            func.count(CollectionItem.id),
            func.coalesce(func.sum(CollectionItem.quantity), 0),
            func.coalesce(func.sum(CollectionItem.quantity * Card.price_usd), 0),
        ).one()
    )
    return {
        "items": [ci.to_dict() for ci in page.items],
        "pagination": {
            "page": page.page,
            "per_page": page.per_page,
            "pages": page.pages,
            "total_items": page.total,
        },
        "unique_cards": unique,
        "total_cards": int(total),
        "estimated_value": round(float(value), 2),
    }


@bp.post("")
@jwt_required()
def add():
    data = CollectionAddSchema().load(request.get_json(silent=True) or {})
    card = get_card(data["card_id"])
    if card is None:
        abort(404, description="Card not found. Search for it first.")

    # Upsert: owning a card already means adding to its quantity, not a second row.
    item = CollectionItem.query.filter_by(user_id=current_user_id(), card_id=card.id).first()
    if item:
        item.quantity = min(item.quantity + data["quantity"], 999)
        status = 200
    else:
        item = CollectionItem(user_id=current_user_id(), card_id=card.id, quantity=data["quantity"])
        db.session.add(item)
        status = 201
    db.session.commit()
    return item.to_dict(), status


@bp.patch("/<int:item_id>")
@jwt_required()
def update(item_id):
    item = get_owned_or_404(CollectionItem, item_id)
    data = CollectionUpdateSchema().load(request.get_json(silent=True) or {})
    item.quantity = data["quantity"]
    db.session.commit()
    return item.to_dict()


@bp.delete("/<int:item_id>")
@jwt_required()
def destroy(item_id):
    item = get_owned_or_404(CollectionItem, item_id)
    db.session.delete(item)
    db.session.commit()
    return "", 204
