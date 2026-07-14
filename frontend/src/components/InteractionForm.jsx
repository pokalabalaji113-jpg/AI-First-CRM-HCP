import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { clearFlash } from "../store/formSlice";
import { setDraft } from "../store/chatSlice";
import VoiceNoteButton from "./VoiceNoteButton";

/**
 * The LEFT panel — "Interaction Details".
 *
 * The widgets LOOK exactly like the reference screenshot (dropdowns, date/time
 * pickers, Search/Add buttons, voice note, radio sentiment) — BUT every one is
 * DISABLED for manual entry. The values are a live mirror of the AI-controlled
 * Redux state. Buttons route the rep back to the AI Assistant instead of letting
 * them type into the form. Fields the AI just changed briefly flash.
 */

// A read-only text/textarea field.
function TextField({ label, value, flash, full, multiline }) {
  return (
    <div className={`field ${full ? "field--full" : ""}`}>
      <label>{label}</label>
      {multiline ? (
        <textarea readOnly value={value || ""} className={flash ? "flash" : ""} rows={2} placeholder="—" />
      ) : (
        <input readOnly value={value || ""} className={flash ? "flash" : ""} placeholder="—" />
      )}
    </div>
  );
}

// Looks like a <select> dropdown (chevron), but disabled — AI sets the value.
function SelectField({ label, value, flash, placeholder }) {
  return (
    <div className="field">
      <label>{label}</label>
      <div className={`select-look ${flash ? "flash" : ""}`}>
        <span className={value ? "" : "muted"}>{value || placeholder}</span>
        <span className="chevron">▾</span>
      </div>
    </div>
  );
}

// Looks like a date/time picker with a trailing icon, but disabled.
function PickerField({ label, value, flash, icon, placeholder }) {
  return (
    <div className="field">
      <label>{label}</label>
      <div className={`select-look ${flash ? "flash" : ""}`}>
        <span className={value ? "" : "muted"}>{value || placeholder}</span>
        <span className="chevron">{icon}</span>
      </div>
    </div>
  );
}

// A field with a right-aligned action button (Materials / Samples).
function ButtonField({ label, value, flash, buttonText, onClick, empty }) {
  return (
    <div className="field">
      <div className="field-head">
        <label>{label}</label>
        <button type="button" className="mini-btn" onClick={onClick}>
          {buttonText}
        </button>
      </div>
      <div className={`chip-box ${flash ? "flash" : ""}`}>
        {value ? <span className="value-chip">{value}</span> : <span className="muted">{empty}</span>}
      </div>
    </div>
  );
}

function SentimentRadio({ current }) {
  const options = [
    { key: "Positive", emoji: "😊" },
    { key: "Neutral", emoji: "😐" },
    { key: "Negative", emoji: "☹️" },
  ];
  return (
    <div className="field field--full">
      <label>Observed / Inferred HCP Sentiment</label>
      <div className="radio-row">
        {options.map((o) => (
          <label key={o.key} className={`radio ${current === o.key ? `radio--on radio--${o.key.toLowerCase()}` : ""}`}>
            <span className={`dot ${current === o.key ? "dot--on" : ""}`} />
            <span className="emoji">{o.emoji}</span>
            {o.key}
          </label>
        ))}
      </div>
    </div>
  );
}

export default function InteractionForm() {
  const { data, flashFields } = useSelector((s) => s.form);
  const dispatch = useDispatch();
  const flash = (f) => flashFields.includes(f);

  useEffect(() => {
    if (flashFields.length) {
      const t = setTimeout(() => dispatch(clearFlash()), 1600);
      return () => clearTimeout(t);
    }
  }, [flashFields, dispatch]);

  return (
    <section className="panel panel--form">
      <div className="panel__header">
        <h2>Interaction Details</h2>
        {data.id ? <span className="badge">#{data.id}</span> : null}
      </div>

      <p className="readonly-note">
        🔒 Every field is filled by the AI Assistant — manual typing is disabled. Use the
        chat (or 🎤 voice) on the right.
      </p>

      <div className="grid">
        <SelectField label="HCP Name" value={data.hcp_name} flash={flash("hcp_name")} placeholder="Search or select HCP…" />
        <SelectField
          label="Interaction Type"
          value={data.interaction_type}
          flash={flash("interaction_type")}
          placeholder="Meeting"
        />
        <PickerField label="Date" value={data.date} flash={flash("date")} icon="📅" placeholder="DD-MM-YYYY" />
        <PickerField label="Time" value={data.time} flash={flash("time")} icon="🕐" placeholder="HH:MM" />

        <TextField label="Attendees" value={data.attendees} flash={flash("attendees")} full />

        <div className="field field--full">
          <div className="field-head">
            <label>Topics Discussed</label>
            <VoiceNoteButton />
          </div>
          <textarea
            readOnly
            value={data.topics_discussed || ""}
            className={flash("topics_discussed") ? "flash" : ""}
            rows={2}
            placeholder="Enter key discussion points…"
          />
        </div>

        <ButtonField
          label="Materials Shared"
          value={data.materials_shared}
          flash={flash("materials_shared")}
          buttonText="🔍 Search/Add"
          empty="No materials added"
          onClick={() => dispatch(setDraft("Add material shared: "))}
        />
        <ButtonField
          label="Samples Distributed"
          value={data.samples_distributed}
          flash={flash("samples_distributed")}
          buttonText="➕ Add Sample"
          empty="No samples added"
          onClick={() => dispatch(setDraft("Add sample distributed: "))}
        />

        <SentimentRadio current={data.sentiment} />

        <TextField label="Outcomes" value={data.outcomes} flash={flash("outcomes")} full multiline />
        <TextField label="Follow-up Actions" value={data.follow_up_actions} flash={flash("follow_up_actions")} full multiline />
      </div>

      {data.ai_suggested_followups?.length > 0 && (
        <div className="ai-suggest">
          <label>✨ AI Suggested Follow-ups</label>
          <ul>
            {data.ai_suggested_followups.map((s, i) => (
              <li key={i}>+ {s}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
