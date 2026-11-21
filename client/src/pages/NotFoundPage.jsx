import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="empty">
      <h2>Page not found</h2>
      <p>That address doesn't match anything in Deckforge.</p>
      <Link className="btn btn-primary" to="/decks">Go to your decks</Link>
    </div>
  );
}
