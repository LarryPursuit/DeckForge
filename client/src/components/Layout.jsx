import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/auth-context";

export function ProtectedRoute() {
  const { user, status } = useAuth();
  const location = useLocation();
  if (status === "checking") return <p className="page-loading">Opening your deckbox…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

export function GuestRoute() {
  const { user, status } = useAuth();
  if (status === "checking") return null;
  if (user) return <Navigate to="/decks" replace />;
  return <Outlet />;
}

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to={user ? "/decks" : "/login"} className="wordmark">
            <span className="wordmark-mark" aria-hidden="true" />
            Deckforge
          </NavLink>
          {user && (
            <nav className="nav" aria-label="Main">
              <NavLink to="/decks">Decks</NavLink>
              <NavLink to="/collection">Collection</NavLink>
              <NavLink to="/search">Find cards</NavLink>
            </nav>
          )}
          {user && (
            <div className="topbar-user">
              <span>{user.username}</span>
              <button type="button" className="btn-link on-felt" onClick={() => logout()}>
                Log out
              </button>
            </div>
          )}
        </div>
      </header>
      <main id="main" className="page">
        <Outlet />
      </main>
      <footer className="footer">
        Card data and images from <a href="https://scryfall.com">Scryfall</a>. Deckforge is
        unofficial Fan Content permitted under the Wizards of the Coast Fan Content Policy.
      </footer>
    </>
  );
}
