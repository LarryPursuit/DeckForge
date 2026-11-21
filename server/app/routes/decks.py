from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import CollectionItem, Deck, DeckCard, utcnow
from ..schemas import DeckCardAddSchema, DeckCardUpdateSchema, DeckSchema
from ..scryfall import get_card
from ..utils import current_user_id, get_owned_or_404

bp = Blueprint("decks", __name__, url_prefix="/api/decks")


def deck_status(deck, user_id):
    """Compare the deck with the user's collection.

    Owned copies are shared across the main deck and sideboard: the main deck
    claims them first, and whatever is left counts toward the sideboard.
    """
    owned = {
        ci.card_id: ci.quantity
        for ci in CollectionItem.query.filter_by(user_id=user_id).all()
    }
    remaining = dict(owned)
    ordered = sorted(deck.deck_cards, key=lambda dc: (dc.board != "main", dc.card.name))

    rows, missing_cost, need_total, have_total = [], 0.0, 0, 0
    for dc in ordered:
        have = min(remaining.get(dc.card_id, 0), dc.quantity)
        remaining[dc.card_id] = remaining.get(dc.card_id, 0) - have
        missing = dc.quantity - have
        missing_cost += missing * (dc.card.price_usd or 0)
        need_total += dc.quantity
        have_total += have
        rows.append(
            {
                "id": dc.id,
                "board": dc.board,
                "need": dc.quantity,
                "have": have,
                "missing": missing,
                "status": "owned" if missing == 0 else ("partial" if have else "missing"),
                "card": dc.card.to_dict(),
            }
        )

    return {
        "cards": rows,
        "totals": {
            "cards": need_total,
            "owned": have_total,
            "missing": need_total - have_total,
            "percent_owned": round(100 * have_total / need_total) if need_total else 0,
            "missing_cost": round(missing_cost, 2),
        },
    }


def _deck_payload(deck):
    return {**deck.summary(), **deck_status(deck, current_user_id())}


@bp.get("")
@jwt_required()
def index():
    # Load every deck's cards in two extra queries instead of two per deck.
    decks = (
        Deck.query.filter_by(user_id=current_user_id())
        .options(selectinload(Deck.deck_cards).selectinload(DeckCard.card))
        .order_by(Deck.updated_at.desc())
        .all()
    )
    return {"decks": [d.summary() for d in decks]}


@bp.post("")
@jwt_required()
def create():
    data = DeckSchema().load(request.get_json(silent=True) or {})
    deck = Deck(user_id=current_user_id(), **data)
    db.session.add(deck)
    db.session.commit()
    return _deck_payload(deck), 201


@bp.get("/<int:deck_id>")
@jwt_required()
def show(deck_id):
    return _deck_payload(get_owned_or_404(Deck, deck_id))


@bp.patch("/<int:deck_id>")
@jwt_required()
def update(deck_id):
    deck = get_owned_or_404(Deck, deck_id)
    data = DeckSchema(partial=True).load(request.get_json(silent=True) or {})
    for key, value in data.items():
        setattr(deck, key, value)
    db.session.commit()
    return _deck_payload(deck)


@bp.delete("/<int:deck_id>")
@jwt_required()
def destroy(deck_id):
    deck = get_owned_or_404(Deck, deck_id)
    db.session.delete(deck)
    db.session.commit()
    return "", 204


@bp.post("/<int:deck_id>/cards")
@jwt_required()
def add_card(deck_id):
    deck = get_owned_or_404(Deck, deck_id)
    data = DeckCardAddSchema().load(request.get_json(silent=True) or {})
    card = get_card(data["card_id"])
    if card is None:
        abort(404, description="Card not found. Search for it first.")

    dc = DeckCard.query.filter_by(deck_id=deck.id, card_id=card.id, board=data["board"]).first()
    if dc:
        dc.quantity = min(dc.quantity + data["quantity"], 99)
    else:
        dc = DeckCard(deck=deck, card=card, quantity=data["quantity"], board=data["board"])
        db.session.add(dc)
    deck.updated_at = utcnow()
    db.session.commit()
    return _deck_payload(deck), 201


def _get_deck_card(deck, deck_card_id):
    dc = db.session.get(DeckCard, deck_card_id)
    # The deck was already ownership-checked; make sure this row lives in it.
    if dc is None or dc.deck_id != deck.id:
        abort(404, description="Card is not in this deck")
    return dc


@bp.patch("/<int:deck_id>/cards/<int:deck_card_id>")
@jwt_required()
def update_card(deck_id, deck_card_id):
    deck = get_owned_or_404(Deck, deck_id)
    dc = _get_deck_card(deck, deck_card_id)
    data = DeckCardUpdateSchema().load(request.get_json(silent=True) or {})

    if "board" in data and data["board"] != dc.board:
        # Moving to the other board merges with an existing row there.
        other = DeckCard.query.filter_by(deck_id=deck.id, card_id=dc.card_id, board=data["board"]).first()
        if other:
            other.quantity = min(other.quantity + data.get("quantity", dc.quantity), 99)
            db.session.delete(dc)
            db.session.commit()
            return _deck_payload(deck)
        dc.board = data["board"]
    if "quantity" in data:
        dc.quantity = data["quantity"]
    deck.updated_at = utcnow()
    db.session.commit()
    return _deck_payload(deck)


@bp.delete("/<int:deck_id>/cards/<int:deck_card_id>")
@jwt_required()
def remove_card(deck_id, deck_card_id):
    deck = get_owned_or_404(Deck, deck_id)
    dc = _get_deck_card(deck, deck_card_id)
    db.session.delete(dc)
    deck.updated_at = utcnow()
    db.session.commit()
    return _deck_payload(deck)
