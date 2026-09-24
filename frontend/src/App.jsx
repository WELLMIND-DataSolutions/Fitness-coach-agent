import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Login from "./Login";
import { api, clearToken, getToken } from "./api";
import "./App.css";

const WELCOME = {
  role: "coach",
  text: "Assalam-o-Alaikum! I'm FitCoach. Tell me your fitness goal and we'll get started.",
};
const NOTIFICATION_POLL_MS = 30000;

function App() {
  const [loggedIn, setLoggedIn] = useState(() => Boolean(getToken()));
  const [messages, setMessages] = useState([WELCOME]);
  const [notifications, setNotifications] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  const logout = useCallback(() => {
    clearToken();
    setLoggedIn(false);
    setMessages([WELCOME]);
    setNotifications([]);
  }, []);

  // Any 401 means the token is gone or expired: send the user back to login.
  const guard = useCallback(
    (err) => {
      if (err.status === 401) logout();
      return err;
    },
    [logout]
  );

  useEffect(() => {
    if (!loggedIn) return;
    api
      .history()
      .then((rows) => {
        if (rows.length) setMessages(rows.map((r) => ({ role: r.role, text: r.text })));
      })
      .catch(guard);
  }, [loggedIn, guard]);

  useEffect(() => {
    if (!loggedIn) return;
    const poll = () => api.notifications().then(setNotifications).catch(guard);
    poll();
    const id = setInterval(poll, NOTIFICATION_POLL_MS);
    return () => clearInterval(id);
  }, [loggedIn, guard]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const dismiss = async (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    api.markRead(id).catch(guard);
  };

  const newChat = async () => {
    if (!window.confirm("Clear this conversation? Your profile and logs stay saved.")) return;
    try {
      await api.clearHistory();
      setMessages([WELCOME]);
    } catch (err) {
      guard(err);
    }
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setLoading(true);
    try {
      const data = await api.chat(text);
      setMessages((prev) => [...prev, { role: "coach", text: data.reply }]);
    } catch (err) {
      guard(err);
      setMessages((prev) => [...prev, { role: "coach", text: err.message, isError: true }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!loggedIn) return <Login onSuccess={() => setLoggedIn(true)} />;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">FC</div>
          <div className="brand-text">
            <span className="brand-name">FitCoach</span>
            <span className="brand-sub">AI fitness assistant</span>
          </div>
        </div>
        <div className="header-right">
          <button className="ghost-btn" onClick={newChat}>
            New chat
          </button>
          <button className="logout-btn" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {notifications.length > 0 && (
        <div className="reminders" role="status" aria-live="polite">
          {notifications.map((n) => (
            <div key={n.id} className="reminder">
              <span className="reminder-text">Reminder: {n.message}</span>
              <button onClick={() => dismiss(n.id)} aria-label={`Dismiss reminder: ${n.message}`}>
                Done
              </button>
            </div>
          ))}
        </div>
      )}

      <main className="chat-window" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`message-row ${m.role === "user" ? "row-user" : "row-coach"}`}>
            {m.role === "coach" && <div className="avatar">FC</div>}
            <div
              className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-coach"} ${m.isError ? "bubble-error" : ""}`}
            >
              {m.role === "coach" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown> : m.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row row-coach">
            <div className="avatar">FC</div>
            <div className="bubble bubble-coach typing" aria-label="FitCoach is typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </main>

      <footer className="composer">
        <label className="sr-only" htmlFor="composer">Message</label>
        <textarea
          id="composer"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question or log a meal, workout or weight..."
          rows={1}
          maxLength={2000}
        />
        <button onClick={sendMessage} disabled={loading || !input.trim()}>
          Send
        </button>
      </footer>
    </div>
  );
}

export default App;