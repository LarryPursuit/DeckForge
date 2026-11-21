import json
from datetime import datetime, timezone

from sqlalchemy.orm import validates

from .extensions import bcrypt, db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    collection_items = db.relationship(
        "CollectionItem", back_populates="user", cascade="all, delete-orphan"
    )
    decks = db.relationship("Deck", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @validates("email")
    def normalize_email(self, _key, value):
        return value.strip().lower()

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class Card(db.Model):
    """A Magic card cached from Scryfall. The primary key is Scryfall's own id."""

    __tablename__ = "cards"

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    set_code = db.Column(db.String(10))
    set_name = db.Column(db.String(120))
    collector_number = db.Column(db.String(20))
    rarity = db.Column(db.String(20))
    type_line = db.Column(db.String(200))
    mana_cost = db.Column(db.String(80))
    cmc = db.Column(db.Float)
    colors = db.Column(db.String(40))  # JSON list, e.g. '["R"]'
    image_url = db.Column(db.String(300))
    image_small = db.Column(db.String(300))
    price_usd = db.Column(db.Float)
    scryfall_uri = db.Column(db.String(300))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "set_code": self.set_code,
            "set_name": self.set_name,
            "collector_number": self.collector_number,
            "rarity": self.rarity,
            "type_line": self.type_line,
            "mana_cost": self.mana_cost,
            "cmc": self.cmc,
            "colors": json.loads(self.colors) if self.colors else [],
            "image_url": self.image_url,
            "image_small": self.image_small,
            "price_usd": self.price_usd,
            "scryfall_uri": self.scryfall_uri,
        }


class CollectionItem(db.Model):
    __tablename__ = "collection_items"
    __table_args__ = (db.UniqueConstraint("user_id", "card_id", name="uq_collection_user_card"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    card_id = db.Column(db.String(36), db.ForeignKey("cards.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="collection_items")
    card = db.relationship("Card")

    def to_dict(self):
        return {
            "id": self.id,
            "quantity": self.quantity,
            "added_at": self.added_at.isoformat(),
            "card": self.card.to_dict(),
        }


class Deck(db.Model):
    __tablename__ = "decks"

    FORMATS = ("casual", "standard", "pioneer", "modern", "commander", "pauper")

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    format = db.Column(db.String(20), nullable=False, default="casual")
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="decks")
    deck_cards = db.relationship(
        "DeckCard", back_populates="deck", cascade="all, delete-orphan", order_by="DeckCard.id"
    )

    def summary(self):
        main = sum(dc.quantity for dc in self.deck_cards if dc.board == "main")
        side = sum(dc.quantity for dc in self.deck_cards if dc.board == "side")
        cover = next((dc.card.image_url for dc in self.deck_cards), None)
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "description": self.description or "",
            "main_count": main,
            "side_count": side,
            "cover_image": cover,
            "updated_at": self.updated_at.isoformat(),
        }


class DeckCard(db.Model):
    __tablename__ = "deck_cards"
    __table_args__ = (
        db.UniqueConstraint("deck_id", "card_id", "board", name="uq_deck_card_board"),
    )

    BOARDS = ("main", "side")

    id = db.Column(db.Integer, primary_key=True)
    deck_id = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False, index=True)
    card_id = db.Column(db.String(36), db.ForeignKey("cards.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    board = db.Column(db.String(10), nullable=False, default="main")

    deck = db.relationship("Deck", back_populates="deck_cards")
    card = db.relationship("Card")
