import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import { FORMATS } from "../constants";


export default function DecksPage() {
  const [decks, setDecks] = useState(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    apiFetch("/api/decks")
      .then((d) => setDecks(d.decks))
      .catch((err) => setError(err.message));
  }, []);

  if (!decks && !error) return <p className="page-loading">Loading your decks…</p>;

  return (
    <>
      <div className="page-head page-head-row">
        <div>
          <h1>Decks</h1>
          <p className="lede">Build a deck and see which cards you still need.</p>
        </div>
        {!creating && (
          <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
            New deck
          </button>
        )}
      </div>

      {error && <p className="callout callout-error" role="alert">{error}</p>}
      {creating && <NewDeckForm onCancel={() => setCreating(false)} />}

      {decks && decks.length === 0 && !creating && (
        <div className="empty">
          <h2>No decks yet</h2>
          <p>Start a deck, add cards from any set, and Deckforge will mark the ones already in your collection.</p>
          <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
            New deck
          </button>
        </div>
      )}

      {decks && decks.length > 0 && (
        <ul className="deck-list">
          {decks.map((d) => (
            <li key={d.id}>
              <Link to={`/decks/${d.id}`} className="deck-row">
                <span className="deck-cover" aria-hidden="true">
                  {d.cover_image && <img src={d.cover_image} alt="" />}
                </span>
                <span className="deck-row-text">
                  <span className="deck-row-name">{d.name}</span>
                  <span className="deck-row-sub">
                    <span className="format-tag">{d.format}</span>
                    {d.main_count} cards{d.side_count > 0 && `, ${d.side_count} in sideboard`}
                  </span>
                  {d.description && <span className="deck-row-desc">{d.description}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function NewDeckForm({ onCancel }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", format: "casual", description: "" });
  const [fields, setFields] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim()) {
      setFields({ name: ["Give your deck a name."] });
      return;
    }
    setBusy(true);
    try {
      const deck = await apiFetch("/api/decks", { method: "POST", body: { ...form, name: form.name.trim() } });
      navigate(`/decks/${deck.id}`);
    } catch (err) {
      setError(err.message);
      setFields(err.fields);
      setBusy(false);
    }
  }

  return (
    <form className="panel deck-form" onSubmit={submit} noValidate>
      <h2>New deck</h2>
      {error && <p className="callout callout-error" role="alert">{error}</p>}
      <div className="form-row">
        <label className="field grow">
          <span>Name</span>
          <input name="name" value={form.name} onChange={update} autoFocus aria-invalid={!!fields.name} />
          {fields.name && <span className="field-error">{fields.name.join(" ")}</span>}
        </label>
        <label className="field">
          <span>Format</span>
          <select name="format" value={form.format} onChange={update}>
            {FORMATS.map((f) => (
              <option key={f} value={f}>
                {f[0].toUpperCase() + f.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="field">
        <span>Notes (optional)</span>
        <textarea name="description" rows="2" value={form.description} onChange={update} />
      </label>
      <div className="form-actions">
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Creating…" : "Create deck"}
        </button>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
