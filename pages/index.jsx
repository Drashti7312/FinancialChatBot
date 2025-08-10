// pages/index.jsx
import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { useRouter } from "next/router";
import {
  uploadDocument,
  addLink,
  getSupportedLanguages,
  selectLanguage,
  getSessions,
  chatMessage,
  getCharts
} from "../utils/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const userId = process.env.NEXT_PUBLIC_DEFAULT_USER_ID;
  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkTitle, setLinkTitle] = useState("");
  const [supportedLanguages, setSupportedLanguages] = useState([]);
  const [selectedLanguage, setSelectedLanguage] = useState("");
  const [sessions, setSessions] = useState([]);

  const router = useRouter();

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    getSupportedLanguages().then(res =>
      setSupportedLanguages(res.languages || [])
    );
  }, []);

  useEffect(() => {
    getSessions(userId).then(res =>
      setSessions(res.sessions || [])
    );
  }, [userId]);

  const handleLanguageSelect = async (lang) => {
    setSelectedLanguage(lang);
    if (lang) await selectLanguage(lang, userId, sessionId);
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return alert("Select a file first");
    await uploadDocument({ session_id: sessionId, user_id: userId, file: selectedFile });
    setSelectedFile(null);
  };

  const handleAddLink = async () => {
    if (!linkUrl.trim() || !linkTitle.trim()) return;
    await addLink({ session_id: sessionId, user_id: userId, url: linkUrl, title: linkTitle });
    setLinkUrl("");
    setLinkTitle("");
  };

  const sendMessage = async () => {
    if (!message.trim()) return;
    setChatHistory(prev => [...prev, { sender: "user", text: message }]);
    const data = await chatMessage({ session_id: sessionId, user_id: userId, message });
    setChatHistory(prev => [...prev, { sender: "bot", text: data.response || "No response" }]);
    setMessage("");
  };

  const handleDownloadCharts = async () => {
    try {
      const data = await getCharts(sessionId, userId);
      if (!data.charts || data.charts.length === 0) {
        alert("No charts available for this session");
        return;
      }
      data.charts.forEach((chart, idx) => {
        const link = document.createElement("a");
        link.href = `data:image/png;base64,${chart.chart_data}`;
        link.download = chart.filename || `chart_${idx + 1}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
      alert(`${data.charts.length} chart(s) downloaded`);
    } catch (error) {
      console.error("Error downloading charts:", error);
      alert("Error downloading charts");
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "Arial, sans-serif" }}>
      <h1>Financial Intelligence Chatbot</h1>
      <div>
        <strong>Current Session ID:</strong> <code>{sessionId}</code>
        <button
          onClick={handleDownloadCharts}
          style={{
            marginLeft: "1rem",
            background: "#4CAF50",
            color: "white",
            padding: "5px 10px",
            border: "none",
            borderRadius: "5px",
            cursor: "pointer"
          }}
        >
          Download Charts
        </button>
      </div>

      {/* Language Selection */}
      <div style={{ marginTop: "1rem" }}>
        <label><strong>Select Language:</strong></label>
        <select value={selectedLanguage} onChange={(e) => handleLanguageSelect(e.target.value)}>
          <option value="">-- Select --</option>
          {supportedLanguages.map((lang, idx) => (
            <option key={idx} value={lang}>{lang}</option>
          ))}
        </select>
      </div>

      {/* Past Sessions */}
      <div style={{ marginTop: "1rem" }}>
        <label><strong>Past Sessions:</strong></label>
        <ul>
          {sessions.map((session, idx) => (
            <li key={session.session_id}>
              <button onClick={() => router.push(`/chat/${session.session_id}`)}>
                Session {idx + 1} - {session.created_at}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Chat Box */}
      <div style={{
        border: "1px solid #ddd",
        height: 400,
        overflowY: "auto",
        padding: "1rem",
        marginTop: "1rem",
        backgroundColor: "#f9f9f9"
      }}>
        {chatHistory.length === 0 && <p>Start chatting...</p>}
        {chatHistory.map((msg, idx) => (
          <div key={idx} style={{
            textAlign: msg.sender === "user" ? "right" : "left",
            marginBottom: "0.5rem"
          }}>
            <div style={{
              display: "inline-block",
              backgroundColor: msg.sender === "user" ? "#0070f3" : "#eaeaea",
              color: msg.sender === "user" ? "white" : "black",
              padding: "0.5rem 1rem",
              borderRadius: "20px",
              maxWidth: "80%",
              wordWrap: "break-word",
              textAlign: "left"
            }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.text}
              </ReactMarkdown>
            </div>
          </div>
        ))}
      </div>

      {/* Message Input */}
      <div style={{ marginTop: "1rem", display: "flex" }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
          style={{ flexGrow: 1, padding: "0.5rem", fontSize: "1rem" }}
        />
        <button onClick={sendMessage} style={{ marginLeft: "0.5rem" }}>Send</button>
      </div>

      {/* File Upload */}
      <div style={{ marginTop: "2rem" }}>
        <h3>Upload Document</h3>
        <input
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.csv"
          onChange={(e) => setSelectedFile(e.target.files[0])}
        />
        <button onClick={handleFileUpload} style={{ marginLeft: "0.5rem" }}>Upload</button>
      </div>

      {/* Add Link */}
      <div style={{ marginTop: "2rem" }}>
        <h3>Add Link</h3>
        <input
          type="text"
          placeholder="Enter URL"
          value={linkUrl}
          onChange={(e) => setLinkUrl(e.target.value)}
          style={{ width: "100%", marginBottom: "0.5rem" }}
        />
        <input
          type="text"
          placeholder="Enter Title"
          value={linkTitle}
          onChange={(e) => setLinkTitle(e.target.value)}
          style={{ width: "100%", marginBottom: "0.5rem" }}
        />
        <button onClick={handleAddLink}>Add Link</button>
      </div>
    </div>
  );
}
