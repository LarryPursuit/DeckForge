import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import CardImage from "../components/CardImage";
import Pagination from "../components/Pagination";
import useDebounce from "../hooks/useDebounce";

const money = (n) => `$${n.toFixed(2)}`;
const PER_PAGE = 24;

const COLORS = [
  { value: "W", label: "White" },
  { value: "U", label: "Blue" },
  { value: "B", label: "Black" },
  { value: "R", label: "Red" },
  { value: "G", label: "Green" },
  { value: "M", label: "Multicolor" },
  { value: "C", label: "Colorless" },
];

const SORTS = [
  { value: "name", label: "Name" },
  { value: "price", label: "Price, highest first" },
  { value: "quantity", label: "Copies, most first" },
  { value: "recent", label: "Recently added" },
];

export default function CollectionPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [color, setColor] = useState("");
  const [sort, setSort] = useState("name");
  const [page, setPage] = useState(1);
  const q = useDebounce(search.trim(), 300);

  const load = useCallback(() => {
    const params = new URLSearchParams({ q, sort, page, per_page: PER_PAGE });
    if (color) params.set("color", color);
    return apiFetch(`/api/collection?${params}`)
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, [q, color, sort, page]);

  useEffect(() => {
    load();
  }, [load]);

  // Any new filter starts again from page 1.
  const changeFilter = (setter) => (value) => {
    setter(value);
    setPage(1);
  };

  async function setQuantity(item, quantity) {
    try {
      if (quantity < 1) await apiFetch(`/api/collection/${item.id}`, { method: "DELETE" });
      else await apiFetch(`/api/collection/${item.id}`, { method: "PATCH", body: { quantity } });
      // Removing the last card on a page steps back one page.
      if (quantity < 1 && data.items.length === 1 && page > 1) setPage(page - 1);
      else await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!data && !error) return <p className="page-loading">Loading your collection…</p>;

  const filtering = Boolean(q || color);
  const isEmpty = data && data.unique_cards === 0;

  return (
    <>
      <div className="page-head page-head-row">
        <div>
          <h1>Collection</h1>
          {data && !isEmpty && (
            <p className="lede">
              {data.total_cards} cards, {data.unique_cards} different. Estimated value{" "}
              {money(data.estimated_value)}.
            </p>
          )}
        </div>
        <Link className="btn btn-primary" to="/search">
          Add cards
        </Link>
      </div>

      {error && <p className="callout callout-error" role="alert">{error}</p>}

      {isEmpty && (
        <div className="empty">
          <h2>Your binder is empty</h2>
          <p>Search for the cards you own and add them here. Your decks will then show what you already have.</p>
          <Link className="btn btn-primary" to="/search">Find cards</Link>
        </div>
      )}

      {data && !isEmpty && (
        <>
          <div className="toolbar">
            <label className="filter">
              <span className="visually-hidden">Filter by name</span>
              <input
                type="search"
                placeholder="Filter by name"
                value={search}
                onChange={(e) => changeFilter(setSearch)(e.target.value)}
              />
            </label>

            <fieldset className="color-filter">
              <legend className="visually-hidden">Filter by color</legend>
              {COLORS.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  className={`color-toggle color-${c.value}`}
                  aria-pressed={color === c.value}
                  title={c.label}
                  onClick={() => changeFilter(setColor)(color === c.value ? "" : c.value)}
                >
                  <span className="visually-hidden">{c.label}</span>
                </button>
              ))}
            </fieldset>

            <label className="sort">
              <span>Sort by</span>
              <select value={sort} onChange={(e) => changeFilter(setSort)(e.target.value)}>
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
          </div>

          <p className="search-status" aria-live="polite">
            {filtering
              ? `${data.pagination.total_items} of ${data.unique_cards} cards match.`
              : `${data.unique_cards} different cards.`}
            {filtering && (
              <button
                type="button"
                className="btn-link"
                onClick={() => {
                  setSearch("");
                  setColor("");
                  setPage(1);
                }}
              >
                Clear filters
              </button>
            )}
          </p>

          {data.items.length > 0 && (
            <ul className="pocket-grid">
              {data.items.map((item) => (
                <li key={item.id} className="pocket">
                  <div className={`stack ${item.quantity > 1 ? "stack-many" : ""}`}>
                    <CardImage card={item.card} />
                  </div>
                  <div className="pocket-meta">
                    <span className="pocket-name">{item.card.name}</span>
                    <span className="pocket-sub">
                      {item.card.set_code?.toUpperCase()}
                      {item.card.price_usd != null && `, est. ${money(item.card.price_usd)} each`}
                    </span>
                  </div>
                  <div className="stepper" role="group" aria-label={`Copies of ${item.card.name}`}>
                    <button
                      type="button"
                      onClick={() => setQuantity(item, item.quantity - 1)}
                      aria-label={item.quantity === 1 ? `Remove ${item.card.name}` : "One fewer"}
                    >
                      −
                    </button>
                    <output aria-live="polite">{item.quantity}</output>
                    <button type="button" onClick={() => setQuantity(item, item.quantity + 1)} aria-label="One more">
                      +
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <Pagination page={data.pagination.page} pages={data.pagination.pages} onChange={setPage} />
        </>
      )}
    </>
  );
}
