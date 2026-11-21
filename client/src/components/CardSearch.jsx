import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import useDebounce from "../hooks/useDebounce";
import CardImage from "./CardImage";

const fetchPage = (q, page, signal) =>
  apiFetch(`/api/cards/search?q=${encodeURIComponent(q)}&page=${page}`, { signal });

const fromResponse = (data, previous) => ({
  status: "done",
  cards: [...previous, ...data.cards],
  total: data.total,
  page: data.page,
  hasMore: data.has_more,
  error: "",
});

/**
 * Debounced Scryfall search through our Flask proxy.
 * `onPick(card)` runs the page's action (add to collection, add to deck)
 * and resolves to a short confirmation message.
 */
export default function CardSearch({ actionLabel, onPick, autoFocus = false, compact = false }) {
  const [query, setQuery] = useState("");
  const debounced = useDebounce(query.trim(), 400);
  const [state, setState] = useState({ status: "idle", cards: [], total: 0, page: 1, hasMore: false, error: "" });
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (debounced.length < 2) {
      setState({ status: "idle", cards: [], total: 0, page: 1, hasMore: false, error: "" });
      return;
    }
    const ctrl = new AbortController();
    setState((s) => ({ ...s, status: "loading", error: "" }));
    fetchPage(debounced, 1, ctrl.signal)
      .then((data) => setState(fromResponse(data, [])))
      .catch((err) => {
        if (err.name !== "AbortError") setState({ status: "error", cards: [], total: 0, page: 1, hasMore: false, error: err.message });
      });
    return () => ctrl.abort();
  }, [debounced]);

  // Scryfall returns up to 175 cards a page; "Show more" fetches the next one.
  async function loadMore() {
    setState((s) => ({ ...s, status: "loading-more", error: "" }));
    try {
      const data = await fetchPage(debounced, state.page + 1);
      setState((s) => fromResponse(data, s.cards));
    } catch (err) {
      setState((s) => ({ ...s, status: "done", error: err.message }));
    }
  }

  async function pick(card) {
    setBusyId(card.id);
    setMessage("");
    try {
      const result = await onPick(card);
      setMessage(result?.message || `Added ${card.name}`);
      if (result?.owned !== undefined) {
        setState((s) => ({
          ...s,
          cards: s.cards.map((c) => (c.id === card.id ? { ...c, owned: result.owned } : c)),
        }));
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className={`search ${compact ? "search-compact" : ""}`}>
      <label className="search-field">
        <span className="visually-hidden">Search cards</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by card name, like “bolt” or “t:dragon”"
          autoFocus={autoFocus}
        />
      </label>

      <p className="search-status" aria-live="polite">
        {state.status === "loading" && "Searching Scryfall…"}
        {state.error && <span className="text-error">{state.error}</span>}
        {state.status === "done" && state.cards.length === 0 && `No cards match “${debounced}”.`}
        {state.status !== "loading" && state.cards.length > 0 &&
          `${state.total} card${state.total === 1 ? "" : "s"} found${state.total > state.cards.length ? `, showing the first ${state.cards.length}` : ""}.`}
        {message && <span className="search-message"> {message}</span>}
      </p>

      {state.cards.length > 0 && (
        <ul className="pocket-grid">
          {state.cards.map((card) => (
            <li key={card.id} className="pocket">
              <CardImage card={card} small={compact} />
              <div className="pocket-meta">
                <span className="pocket-name">{card.name}</span>
                <span className="pocket-sub">
                  {card.set_code?.toUpperCase()}
                  {card.price_usd != null && `, est. $${card.price_usd.toFixed(2)}`}
                </span>
                {card.owned > 0 && <span className="owned-chip">You own {card.owned}</span>}
              </div>
              <button
                type="button"
                className="btn btn-small"
                onClick={() => pick(card)}
                disabled={busyId === card.id}
              >
                {busyId === card.id ? "Adding…" : actionLabel}
              </button>
            </li>
          ))}
        </ul>
      )}

      {state.hasMore && (
        <div className="load-more">
          <button type="button" className="btn" onClick={loadMore} disabled={state.status === "loading-more"}>
            {state.status === "loading-more" ? "Loading…" : "Show more cards"}
          </button>
        </div>
      )}
    </section>
  );
}
