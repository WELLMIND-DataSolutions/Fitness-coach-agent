import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Login from "./Login";
import "./App.css";

const BACKEND_URL = "http://localhost:8000/chat";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("fitcoach_token"));

  const [messages, setMessages] = useState([
    {
      role: "coach",
      text: "Assalam-o-Alaikum! Main FitCoach hoon. Apna fitness goal batayein, shuru karte hain.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLogout = () => {
    localStorage.removeItem("fitcoach_token");
    setToken(null);
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(BACKEND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (res.status === 401) {
        handleLogout();
        throw new Error("Session khatam ho gayi hai — dobara login karein.");
      }

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "coach", text: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "coach",
          text: err.message || "Connection mein masla ho gaya. Backend chal raha hai ya nahi confirm karein.",
          isError: true,
        },
      ]);
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

  if (!token) {
    return <Login onSuccess={(newToken) => setToken(newToken)} />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">FC</div>
          <div className="brand-text">
            <span className="brand-name">FitCoach</span>
            <span className="brand-sub">AI Fitness Assistant</span>
          </div>
        </div>
        <div className="header-right">
          <div className="status-pill">
            <span className="status-dot" />
            Connected
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="chat-window">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`message-row ${m.role === "user" ? "row-user" : "row-coach"}`}
          >
            {m.role === "coach" && <div className="avatar">FC</div>}
            <div
              className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-coach"} ${
                m.isError ? "bubble-error" : ""
              }`}
            >
              {m.role === "coach" ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
              ) : (
                m.text
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row row-coach">
            <div className="avatar">FC</div>
            <div className="bubble bubble-coach typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}

        <div ref={scrollRef} />
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Apna sawal ya update likhein..."
          rows={1}
        />
        <button onClick={sendMessage} disabled={loading || !input.trim()}>
          Send
        </button>
      </footer>
    </div>
  );
}

export default App;
