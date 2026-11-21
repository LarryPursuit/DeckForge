from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required

from ..models import CollectionItem
from ..scryfall import get_card, search_cards
from ..utils import current_user_id

bp = Blueprint("cards", __name__, url_prefix="/api/cards")


def _owned_map(card_ids):
    if not card_ids:
        return {}
    rows = CollectionItem.query.filter(
        CollectionItem.user_id == current_user_id(), CollectionItem.card_id.in_(card_ids)
    ).all()
    return {r.card_id: r.quantity for r in rows}


@bp.get("/search")
@jwt_required()
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return {"error": "Type at least 2 characters to search"}, 400
    page = request.args.get("page", 1, type=int)
    cards, has_more, total = search_cards(query, max(page, 1))
    owned = _owned_map([c.id for c in cards])
    return {
        "cards": [{**c.to_dict(), "owned": owned.get(c.id, 0)} for c in cards],
        "has_more": has_more,
        "total": total,
        "page": page,
    }


@bp.get("/<card_id>")
@jwt_required()
def show(card_id):
    card = get_card(card_id)
    if card is None:
        abort(404, description="Card not found")
    return {**card.to_dict(), "owned": _owned_map([card.id]).get(card.id, 0)}
