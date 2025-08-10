// pages/chat/[sessionId].jsx
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { getSessionChat } from "../../utils/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatPage() {
  const router = useRouter();
  const { sessionId } = router.query;
  const userId = process.env.NEXT_PUBLIC_DEFAULT_USER_ID;

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) return;

    async function fetchChat() {
      try {
        setLoading(true);
        const resp = await getSessionChat(sessionId, userId);

        if (resp.success && Array.isArray(resp.messages)) {
          setMessages(resp.messages);
        } else {
          setError("Invalid chat data");
        }
      } catch (err) {
        console.error("Error fetching chat:", err);
        setError("Failed to fetch chat messages");
      } finally {
        setLoading(false);
      }
    }

    fetchChat();
  }, [sessionId, userId]);

  if (loading) return <p>Loading chat...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;

  return (
    <div style={{ padding: "20px" }}>
      <h1>Chat History for Session: {sessionId}</h1>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {messages.map((msg, idx) => (
          <li
            key={idx}
            style={{
              marginBottom: "10px",
              background: msg.type === "human" ? "#e1f5fe" : "#f3e5f5",
              padding: "10px",
              borderRadius: "6px",
            }}
          >
            <strong>{msg.type === "human" ? "You" : "AI"}:</strong>
            <div style={{ marginTop: "5px" }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
            <div style={{ fontSize: "0.8em", color: "#666" }}>
              {msg.timestamp}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
