// utils/api.js
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;
const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

// Upload Document
export async function uploadDocument({ session_id, user_id, file }) {
  if (!file) throw new Error("No file selected");
  if (!session_id || !user_id) throw new Error("Missing session_id or user_id");

  const fd = new FormData();
  fd.append("file", file);

  const resp = await api.post(
    `/upload?session_id=${encodeURIComponent(session_id)}&user_id=${encodeURIComponent(user_id)}`,
    fd,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return resp.data;
}

// Add Link
export async function addLink({ session_id, user_id, url, title }) {
  const resp = await api.post(
    "/add-link",
    {
      session_id,
      user_id,
      url,
      title
    }
  );
  return resp.data;
}

// Chat
export async function chatMessage(payload) {
  const resp = await api.post("/chat", payload);
  return resp.data;
}

// Fetch Sessions
export async function getSessions(user_id) {
  const resp = await api.get(`/sessions/${encodeURIComponent(user_id)}`);
  return resp.data;
}

// Fetch Session Chat
export async function getSessionChat(session_id, user_id) {
  const resp = await api.get(
    `/chat/${encodeURIComponent(session_id)}/${encodeURIComponent(user_id)}`
  );
  return resp.data;
}

// Fetch Supported Languages
export async function getSupportedLanguages() {
  const resp = await api.get("/supported_languages");
  return resp.data;
}

// Select Language
export async function selectLanguage(language, user_id, session_id) {
  const resp = await api.post(
    `/select_language?language=${encodeURIComponent(language)}&user_id=${encodeURIComponent(user_id)}&session_id=${encodeURIComponent(session_id)}`
  );
  return resp.data;
}

// Get Charts
export async function getCharts(session_id, user_id) {
  const resp = await api.post("/get_charts", { session_id, user_id });
  return resp.data;
}
