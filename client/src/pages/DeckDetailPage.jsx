import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api";
import CardImage from "../components/CardImage";
import CardSearch from "../components/CardSearch";
import ManaCost from "../components/ManaCost";
import { FORMATS, MAX_DECK_COPIES } from "../constants";

const money = (n) => `$${n.toFixed(2)}`;
const MAX_SLOTS = 10;

/** One slot per copy: filled when you own it, hollow when you don't. */
function Slots({ have, need }) {
  const shown = Math.min(need, MAX_SLOTS);
  return (
    <span className="slots" aria-label={`${have} of ${need} owned`}>
      {Array.from({ length: shown }, (_, i) => (
        <span key={i} className={`slot ${i < Math.min(have, shown) ? "slot-owned" : "slot-missing"}`} />
      ))}
      {need > MAX_SLOTS && <span className="slots-more">+{need - MAX_SLOTS}</span>}
    </span>
  );
}

export default function DeckDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [deck, setDeck] = useState(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [adding, setAdding] = useState(false);
  const [board, setBoard] = useState("main");
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = useCallback(
    () =>
      apiFetch(`/api/decks/${id}`)
        .then(setDeck)
        .catch((err) => setError(err.status === 404 || err.status === 403 ? "missing" : err.message)),
    [id]
  );

  useEffect(() => {
    load();
  }, [load]);

  async function mutate(path, options) {
    setError("");
    try {
      setDeck(await apiFetch(path, options));
    } catch (err) {
      setError(err.message);
    }
  }

  const changeQty = (row, quantity) =>
    quantity < 1
      ? mutate(`/api/decks/${id}/cards/${row.id}`, { method: "DELETE" })
      : mutate(`/api/decks/${id}/cards/${row.id}`, { method: "PATCH", body: { quantity } });

  const moveBoard = (row) =>
    mutate(`/api/decks/${id}/cards/${row.id}`, {
      method: "PATCH",
      body: { board: row.board === "main" ? "side" : "main" },
    });

  async function addCard(card) {
    const updated = await apiFetch(`/api/decks/${id}/cards`, {
      method: "POST",
      body: { card_id: card.id, quantity: 1, board },
    });
    setDeck(updated);
    return { message: `Added ${card.name} to the ${board === "main" ? "main deck" : "sideboard"}.` };
  }

  async function deleteDeck() {
    try {
      await apiFetch(`/api/decks/${id}`, { method: "DELETE" });
      navigate("/decks", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  }

  if (error === "missing")
    return (
      <div className="empty">
        <h2>Deck not found</h2>
        <p>It may have been deleted, or it belongs to another account.</p>
        <Link className="btn btn-primary" to="/decks">Back to your decks</Link>
      </div>
    );
  if (!deck) return error ? <p className="callout callout-error">{error}</p> : <p className="page-loading">Loading deck…</p>;

  const main = deck.cards.filter((r) => r.board === "main");
  const side = deck.cards.filter((r) => r.board === "side");
  const shopping = deck.cards.filter((r) => r.missing > 0);
  const t = deck.totals;
  const shown = preview || deck.cards[0]?.card;

  return (
    <>
      <Link to="/decks" className="back-link">All decks</Link>

      {editing ? (
        <EditDeckForm deck={deck} onDone={(d) => { if (d) setDeck(d); setEditing(false); }} />
      ) : (
        <div className="page-head page-head-row">
          <div>
            <h1>{deck.name}</h1>
            <p className="lede">
              <span className="format-tag">{deck.format}</span>
              {deck.main_count} cards{deck.side_count > 0 && `, ${deck.side_count} in sideboard`}
            </p>
            {deck.description && <p className="deck-notes">{deck.description}</p>}
          </div>
          <div className="head-actions">
            <button type="button" className="btn" onClick={() => setEditing(true)}>Edit details</button>
            {confirmDelete ? (
              <>
                <button type="button" className="btn btn-danger" onClick={deleteDeck}>Delete for good</button>
                <button type="button" className="btn-link" onClick={() => setConfirmDelete(false)}>Keep it</button>
              </>
            ) : (
              <button type="button" className="btn" onClick={() => setConfirmDelete(true)}>Delete deck</button>
            )}
          </div>
        </div>
      )}

      {error && <p className="callout callout-error" role="alert">{error}</p>}

      {t.cards > 0 && (
        <div className="completion">
          <div className="completion-text">
            <strong>
              You own {t.owned} of {t.cards} cards
            </strong>
            <span>
              {t.missing === 0
                ? "This deck is ready to play."
                : `${t.missing} missing, about ${money(t.missing_cost)} to finish.`}
            </span>
          </div>
          <div className="completion-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={t.percent_owned} aria-label="Cards owned">
            <span style={{ width: `${t.percent_owned}%` }} />
          </div>
        </div>
      )}

      <div className="deck-layout">
        <div className="deck-main">
          <div className="section-head">
            <h2>Cards</h2>
            <button type="button" className="btn btn-primary btn-small" onClick={() => setAdding((a) => !a)} aria-expanded={adding}>
              {adding ? "Done adding" : "Add cards"}
            </button>
          </div>

          {adding && (
            <div className="panel add-panel">
              <fieldset className="board-choice">
                <legend>Add to</legend>
                {["main", "side"].map((b) => (
                  <label key={b}>
                    <input type="radio" name="board" value={b} checked={board === b} onChange={() => setBoard(b)} />
                    {b === "main" ? "Main deck" : "Sideboard"}
                  </label>
                ))}
              </fieldset>
              <CardSearch actionLabel="Add" onPick={addCard} autoFocus compact />
            </div>
          )}

          {deck.cards.length === 0 && !adding && (
            <div className="empty empty-inline">
              <p>This deck has no cards yet. Add some and Deckforge will check them against your collection.</p>
              <button type="button" className="btn btn-primary" onClick={() => setAdding(true)}>Add cards</button>
            </div>
          )}

          {[["Main deck", main], ["Sideboard", side]].map(
            ([label, rows]) =>
              rows.length > 0 && (
                <section key={label} className="board">
                  <h3>
                    {label} <span className="count">{rows.reduce((n, r) => n + r.need, 0)}</span>
                  </h3>
                  <ul className="card-rows">
                    {rows.map((row) => (
                      <li
                        key={row.id}
                        className={`card-row status-${row.status}`}
                        onMouseEnter={() => setPreview(row.card)}
                        onFocus={() => setPreview(row.card)}
                      >
                        <Slots have={row.have} need={row.need} />
                        <span className="row-name">
                          <span>{row.card.name}</span>
                          <span className="row-type">{row.card.type_line}</span>
                        </span>
                        <span className="row-mana">
                          <ManaCost cost={row.card.mana_cost} />
                        </span>
                        <span className="row-status">
                          {row.status === "owned" && "Owned"}
                          {row.status === "partial" && `Need ${row.missing} more`}
                          {row.status === "missing" && "Not owned"}
                        </span>
                        <span className="row-actions">
                          <span className="stepper stepper-small" role="group" aria-label={`Copies of ${row.card.name}`}>
                            <button type="button" onClick={() => changeQty(row, row.need - 1)} aria-label={row.need === 1 ? `Remove ${row.card.name}` : "One fewer"}>−</button>
                            <output>{row.need}</output>
                            <button type="button" onClick={() => changeQty(row, row.need + 1)} disabled={row.need >= MAX_DECK_COPIES} aria-label="One more">+</button>
                          </span>
                          <button type="button" className="btn-link" onClick={() => moveBoard(row)}>
                            {row.board === "main" ? "To sideboard" : "To main"}
                          </button>
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )
          )}
        </div>

        <aside className="deck-side">
          {shown && (
            <div className="preview">
              <CardImage card={shown} />
            </div>
          )}
          {deck.cards.length > 0 && (
            <div className="panel shopping">
              <h2>Shopping list</h2>
              {shopping.length === 0 ? (
                <p>You own every card in this deck.</p>
              ) : (
                <>
                  <ul>
                    {shopping.map((r) => (
                      <li key={r.id}>
                        <span>
                          {r.missing}× {r.card.name}
                        </span>
                        <span>{r.card.price_usd != null ? money(r.missing * r.card.price_usd) : "no price"}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="shopping-total">
                    <span>Estimated total</span>
                    <strong>{money(t.missing_cost)}</strong>
                  </p>
                  <p className="fine-print">Prices are Scryfall’s daily USD estimates.</p>
                </>
              )}
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function EditDeckForm({ deck, onDone }) {
  const [form, setForm] = useState({ name: deck.name, format: deck.format, description: deck.description });
  const [error, setError] = useState("");
  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    try {
      onDone(await apiFetch(`/api/decks/${deck.id}`, { method: "PATCH", body: form }));
    } catch (err) {
      setError(err.fields?.name?.join(" ") || err.message);
    }
  }

  return (
    <form className="panel deck-form" onSubmit={submit}>
      <h2>Edit details</h2>
      {error && <p className="callout callout-error" role="alert">{error}</p>}
      <div className="form-row">
        <label className="field grow">
          <span>Name</span>
          <input name="name" value={form.name} onChange={update} />
        </label>
        <label className="field">
          <span>Format</span>
          <select name="format" value={form.format} onChange={update}>
            {FORMATS.map((f) => (
              <option key={f} value={f}>{f[0].toUpperCase() + f.slice(1)}</option>
            ))}
          </select>
        </label>
      </div>
      <label className="field">
        <span>Notes</span>
        <textarea name="description" rows="2" value={form.description} onChange={update} />
      </label>
      <div className="form-actions">
        <button className="btn btn-primary">Save changes</button>
        <button type="button" className="btn" onClick={() => onDone(null)}>Cancel</button>
      </div>
    </form>
  );
}
