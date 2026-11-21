"""Marshmallow schemas validate incoming JSON. Responses are built with to_dict()."""

from marshmallow import Schema, ValidationError, fields, validate

from .models import BCRYPT_MAX_BYTES
from .models import Deck, DeckCard

# Scryfall card ids are UUIDs. Checking the shape keeps arbitrary paths
# (like "random" or "named?exact=...") out of the Scryfall URL we build.
scryfall_id = validate.Regexp(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    error="Not a valid card id.",
)


def fits_bcrypt(value):
    """bcrypt only uses the first 72 bytes, and bcrypt 5 raises on anything longer."""
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValidationError("Use 72 bytes or fewer (about 72 letters, fewer with accents or emoji).")


class SignupSchema(Schema):
    username = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=40),
            validate.Regexp(r"^[A-Za-z0-9_]+$", error="Use letters, numbers and underscores only."),
        ],
    )
    email = fields.Email(required=True, validate=validate.Length(max=120))
    password = fields.String(required=True, load_only=True, validate=[validate.Length(min=8), fits_bcrypt])


class LoginSchema(Schema):
    username = fields.String(required=True)  # username or email
    password = fields.String(required=True, load_only=True)


class CollectionAddSchema(Schema):
    card_id = fields.String(required=True, validate=scryfall_id)
    quantity = fields.Integer(load_default=1, validate=validate.Range(min=1, max=999))


class CollectionQuerySchema(Schema):
    """Query-string options for GET /api/collection."""

    q = fields.String(load_default="", validate=validate.Length(max=100))
    color = fields.String(validate=validate.OneOf(["W", "U", "B", "R", "G", "C", "M"]))
    sort = fields.String(load_default="name", validate=validate.OneOf(["name", "price", "quantity", "recent"]))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=48, validate=validate.Range(min=1, max=100))


class CollectionUpdateSchema(Schema):
    quantity = fields.Integer(required=True, validate=validate.Range(min=1, max=999))


class DeckSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=80))
    format = fields.String(load_default="casual", validate=validate.OneOf(Deck.FORMATS))
    description = fields.String(load_default="", validate=validate.Length(max=2000))


class DeckCardAddSchema(Schema):
    card_id = fields.String(required=True, validate=scryfall_id)
    quantity = fields.Integer(load_default=1, validate=validate.Range(min=1, max=99))
    board = fields.String(load_default="main", validate=validate.OneOf(DeckCard.BOARDS))


class DeckCardUpdateSchema(Schema):
    quantity = fields.Integer(validate=validate.Range(min=1, max=99))
    board = fields.String(validate=validate.OneOf(DeckCard.BOARDS))
