import { useCallback, useEffect, useState } from "react";
import { apiFetch, tokenStore } from "../api";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" until we know whether a saved token is still valid
  const [status, setStatus] = useState(tokenStore.get() ? "checking" : "ready");
  const [notice, setNotice] = useState("");

  const logout = useCallback((message = "") => {
    tokenStore.clear();
    setUser(null);
    setNotice(message);
    setStatus("ready");
  }, []);

  // Restore the session after a page refresh.
  useEffect(() => {
    if (!tokenStore.get()) return;
    apiFetch("/api/me")
      .then((data) => setUser(data.user))
      .catch(() => tokenStore.clear())
      .finally(() => setStatus("ready"));
  }, []);

  // apiFetch fires this event on any 401, e.g. an expired token.
  useEffect(() => {
    const onLogout = (e) => logout(e.detail || "Your session ended. Log in again.");
    window.addEventListener("deckforge:logout", onLogout);
    return () => window.removeEventListener("deckforge:logout", onLogout);
  }, [logout]);

  const finish = (data) => {
    tokenStore.set(data.token);
    setUser(data.user);
    setNotice("");
    return data.user;
  };

  const login = (username, password) =>
    apiFetch("/api/login", { method: "POST", body: { username, password } }).then(finish);

  const signup = (fields) => apiFetch("/api/signup", { method: "POST", body: fields }).then(finish);

  return (
    <AuthContext.Provider value={{ user, status, notice, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
