import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendMessage, clearDraft } from "../store/chatSlice";

// Friendly labels for the tool chips shown under assistant replies.
const TOOL_LABELS = {
  log_interaction: "🗒️ Log Interaction",
  edit_interaction: "✏️ Edit Interaction",
  delete_interaction: "🗑️ Delete / Erase",
  search_interactions: "🔍 Search",
  suggest_followups: "✨ Suggest Follow-ups",
};

/**
 * The RIGHT panel — "AI Assistant". This is the ONLY way to fill the form.
 * Sends the rep's message to the LangGraph agent and renders the conversation.
 */
export default function AIChatAssistant() {
  const dispatch = useDispatch();
  const { messages, status, draft } = useSelector((s) => s.chat);
  const [text, setText] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages, status]);

  // A form button (Materials / Samples) pushed a draft -> prefill & focus input.
  useEffect(() => {
    if (draft) {
      setText(draft);
      dispatch(clearDraft());
      inputRef.current?.focus();
    }
  }, [draft, dispatch]);

  const submit = (e) => {
    e.preventDefault();
    const msg = text.trim();
    if (!msg || status === "loading") return;
    dispatch(sendMessage(msg));
    setText("");
  };

  const quicks = [
    "Met Dr. Sharma, discussed OncoBoost efficacy, positive sentiment, shared brochure",
    "Change sentiment to Neutral",
    "Erase the samples distributed",
    "Suggest follow-ups",
  ];

  return (
    <section className="panel panel--chat">
      <div className="panel__header">
        <h2>🤖 AI Assistant</h2>
        <span className="subtitle">Log interaction via chat</span>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble--${m.role}`}>
            <div className="bubble__text">{m.text}</div>
            {m.tools?.length > 0 && (
              <div className="tool-chips">
                {m.tools.map((t, j) => (
                  <span key={j} className="chip">
                    {TOOL_LABELS[t] || t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {status === "loading" && (
          <div className="bubble bubble--assistant">
            <div className="typing"><span /><span /><span /></div>
          </div>
        )}
      </div>

      <div className="quick-row">
        {quicks.map((q) => (
          <button
            key={q}
            className="quick"
            onClick={() => dispatch(sendMessage(q))}
            disabled={status === "loading"}
            title={q}
          >
            {q.length > 26 ? q.slice(0, 26) + "…" : q}
          </button>
        ))}
      </div>

      <form className="chat-input" onSubmit={submit}>
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe interaction…"
          disabled={status === "loading"}
        />
        <button type="submit" disabled={status === "loading" || !text.trim()}>
          ⚡ Log
        </button>
      </form>
    </section>
  );
}
