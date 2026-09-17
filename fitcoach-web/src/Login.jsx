import { useState } from "react";

const AUTH_BASE = "http://localhost:8000";

// props: onSuccess(token) — jab login/register kamyab ho to token upar App.jsx ko de deta hai
function Login({ onSuccess }) {
  const [mode, setMode] = useState("login"); // "login" ya "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Username aur password dono zaroori hain.");
      return;
    }

    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/login" : "/register";
      const res = await fetch(`${AUTH_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Kuch ghalat ho gaya.");
      }

      localStorage.setItem("fitcoach_token", data.access_token);
      onSuccess(data.access_token);
    } catch (err) {
      setError(err.message || "Server se connect nahi ho saka.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="brand-mark auth-brand-mark">FC</div>
        <h1 className="auth-title">
          {mode === "login" ? "FitCoach mein Login karein" : "Naya Account Banayein"}
        </h1>
        <p className="auth-subtitle">
          {mode === "login"
            ? "Apna username aur password daal kar jaari rakhein."
            : "Naya username aur password chun kar account banayein."}
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "..." : mode === "login" ? "Login" : "Register"}
          </button>
        </form>

        <div className="auth-toggle">
          {mode === "login" ? (
            <>
              Account nahi hai?{" "}
              <button type="button" onClick={() => { setMode("register"); setError(""); }}>
                Register karein
              </button>
            </>
          ) : (
            <>
              Pehle se account hai?{" "}
              <button type="button" onClick={() => { setMode("login"); setError(""); }}>
                Login karein
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Login;
