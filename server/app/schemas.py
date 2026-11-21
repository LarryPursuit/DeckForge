"""Marshmallow schemas validate incoming JSON. Responses are built with to_dict()."""

from marshmallow import Schema, fields, validate

from .models import Deck, DeckCard


class SignupSchema(Schema):
    username = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=40),
            validate.Regexp(r"^[A-Za-z0-9_]+$", error="Use letters, numbers and underscores only."),
        ],
    )
    email = fields.Email(required=True, validate=validate.Length(max=120))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    username = fields.String(required=True)  # username or email
    password = fields.String(required=True, load_only=True)


class CollectionAddSchema(Schema):
    card_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
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
    card_id = fields.String(required=True, validate=validate.Length(min=1, max=36))
    quantity = fields.Integer(load_default=1, validate=validate.Range(min=1, max=99))
    board = fields.String(load_default="main", validate=validate.OneOf(DeckCard.BOARDS))


class DeckCardUpdateSchema(Schema):
    quantity = fields.Integer(validate=validate.Range(min=1, max=99))
    board = fields.String(validate=validate.OneOf(DeckCard.BOARDS))
