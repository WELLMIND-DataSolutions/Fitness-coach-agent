import { useState } from "react";
import { api, setToken } from "./api";

function Login({ onSuccess }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isLogin = mode === "login";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Enter a username and password.");
      return;
    }
    setLoading(true);
    try {
      const call = isLogin ? api.login : api.register;
      const data = await call(username.trim(), password);
      setToken(data.access_token);
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(isLogin ? "register" : "login");
    setError("");
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="brand-mark auth-brand-mark">FC</div>
        <h1 className="auth-title">{isLogin ? "Log in to FitCoach" : "Create your account"}</h1>
        <p className="auth-subtitle">
          {isLogin ? "Pick up where you left off." : "Use at least 8 characters for your password."}
        </p>

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <label className="sr-only" htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            maxLength={32}
          />
          <label className="sr-only" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isLogin ? "current-password" : "new-password"}
            maxLength={72}
          />

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}>
            {loading ? (isLogin ? "Logging in..." : "Creating account...") : isLogin ? "Log in" : "Create account"}
          </button>
        </form>

        <div className="auth-toggle">
          {isLogin ? "New to FitCoach? " : "Already have an account? "}
          <button type="button" onClick={switchMode}>
            {isLogin ? "Create an account" : "Log in"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;