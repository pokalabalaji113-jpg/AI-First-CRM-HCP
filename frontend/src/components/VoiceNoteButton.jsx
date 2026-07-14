import { useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { sendMessage } from "../store/chatSlice";

/**
 * "🎤 Summarize from Voice Note (Requires Consent)".
 *
 * Uses the browser Web Speech API to capture the rep's spoken note, then sends
 * the transcript to the SAME LangGraph agent — so the voice note is summarized &
 * logged by the AI, never typed manually into the form.
 */
export default function VoiceNoteButton() {
  const dispatch = useDispatch();
  const [state, setState] = useState("idle"); // idle | listening | unsupported
  const recognitionRef = useRef(null);

  const start = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setState("unsupported");
      return;
    }
    // Consent, as the screenshot label requires.
    if (!window.confirm("Record and transcribe a voice note? (Requires your consent)")) return;

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      if (transcript) dispatch(sendMessage(transcript));
    };
    recognition.onend = () => setState("idle");
    recognition.onerror = () => setState("idle");

    recognitionRef.current = recognition;
    setState("listening");
    recognition.start();
  };

  const stop = () => {
    recognitionRef.current?.stop();
    setState("idle");
  };

  if (state === "unsupported") {
    return <span className="voice-btn voice-btn--off" title="Use Chrome or Edge">🎤 Voice not supported</span>;
  }

  return (
    <button
      type="button"
      className={`voice-btn ${state === "listening" ? "voice-btn--live" : ""}`}
      onClick={state === "listening" ? stop : start}
    >
      {state === "listening" ? "● Listening… (tap to stop)" : "🎤 Summarize from Voice Note"}
    </button>
  );
}
