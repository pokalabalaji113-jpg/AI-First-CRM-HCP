import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// One stable session id per browser tab -> becomes the LangGraph thread_id,
// so the agent remembers the conversation + form across turns.
export function getSessionId() {
  let id = sessionStorage.getItem("hcp_session_id");
  if (!id) {
    id = "sess-" + Math.random().toString(36).slice(2) + "-" + Date.now();
    sessionStorage.setItem("hcp_session_id", id);
  }
  return id;
}

export async function postChat({ message, formData }) {
  const { data } = await api.post("/chat", {
    session_id: getSessionId(),
    message,
    form_data: formData,
  });
  return data; // { reply, form_data, tools_used }
}
