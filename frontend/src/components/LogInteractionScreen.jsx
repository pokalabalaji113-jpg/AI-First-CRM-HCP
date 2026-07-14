import InteractionForm from "./InteractionForm";
import AIChatAssistant from "./AIChatAssistant";

export default function LogInteractionScreen() {
  return (
    <div className="screen">
      <header className="app-header">
        <div>
          <h1>Log HCP Interaction</h1>
          <p>AI-First CRM · Healthcare Professional Module</p>
        </div>
        <span className="powered">Powered by LangGraph + Groq</span>
      </header>

      <div className="layout">
        <InteractionForm />
        <AIChatAssistant />
      </div>
    </div>
  );
}
