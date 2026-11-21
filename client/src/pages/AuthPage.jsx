import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/auth-context";

export default function AuthPage({ mode }) {
  const isSignup = mode === "signup";
  const { login, signup, notice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [fields, setFields] = useState({});
  const [busy, setBusy] = useState(false);

  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setFields({});
    try {
      if (isSignup) await signup(form);
      else await login(form.username, form.password);
      navigate(location.state?.from || "/decks", { replace: true });
    } catch (err) {
      setError(err.message);
      setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  const fieldError = (name) =>
    fields[name] && (
      <span className="field-error" id={`${name}-error`}>
        {fields[name].join(" ")}
      </span>
    );

  return (
    <div className="auth">
      <div className="auth-intro">
        <h1>{isSignup ? "Start your collection" : "Welcome back"}</h1>
        <p>
          Deckforge keeps track of the Magic cards you own and tells you what each of your decks is
          still missing, and what it would cost to finish.
        </p>
      </div>

      <form className="panel auth-form" onSubmit={submit} noValidate>
        {notice && !error && <p className="callout">{notice}</p>}
        {error && (
          <p className="callout callout-error" role="alert">
            {error}
          </p>
        )}

        <label className="field">
          <span>{isSignup ? "Username" : "Username or email"}</span>
          <input
            name="username"
            value={form.username}
            onChange={update}
            autoComplete="username"
            required
            aria-invalid={!!fields.username}
            aria-describedby={fields.username ? "username-error" : undefined}
          />
          {fieldError("username")}
        </label>

        {isSignup && (
          <label className="field">
            <span>Email</span>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={update}
              autoComplete="email"
              required
              aria-invalid={!!fields.email}
              aria-describedby={fields.email ? "email-error" : undefined}
            />
            {fieldError("email")}
          </label>
        )}

        <label className="field">
          <span>Password</span>
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={update}
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            aria-invalid={!!fields.password}
            aria-describedby={fields.password ? "password-error" : undefined}
          />
          {isSignup && !fields.password && <span className="field-hint">At least 8 characters.</span>}
          {fieldError("password")}
        </label>

        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "One moment…" : isSignup ? "Create account" : "Log in"}
        </button>

        <p className="auth-switch">
          {isSignup ? (
            <>
              Already have an account? <Link to="/login">Log in</Link>
            </>
          ) : (
            <>
              New here? <Link to="/signup">Create an account</Link>
            </>
          )}
        </p>
      </form>
    </div>
  );
}
