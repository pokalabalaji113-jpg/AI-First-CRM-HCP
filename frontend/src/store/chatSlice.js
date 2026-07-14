import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { postChat } from "../api";

// Send the rep's message to the LangGraph agent. The store's current form is
// sent along so the agent edits/erases relative to what's on screen.
export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async (message, { getState }) => {
    const formData = getState().form.data;
    const data = await postChat({ message, formData });
    return data; // { reply, form_data, tools_used }
  }
);

const initialState = {
  messages: [
    {
      role: "assistant",
      text:
        "Hi! Log an interaction by just describing it — e.g. \"Met Dr. Smith, " +
        "discussed Product X efficacy, positive sentiment, shared brochure.\" " +
        "I'll fill the form for you. You can also ask me to edit, erase, search, " +
        "or suggest follow-ups.",
      tools: [],
    },
  ],
  status: "idle",
  error: null,
  draft: "", // text pushed into the chat input by form buttons (Materials/Samples)
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setDraft(state, action) {
      state.draft = action.payload;
    },
    clearDraft(state) {
      state.draft = "";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = "loading";
        state.error = null;
        state.messages.push({ role: "user", text: action.meta.arg, tools: [] });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "idle";
        state.messages.push({
          role: "assistant",
          text: action.payload.reply,
          tools: action.payload.tools_used || [],
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "idle";
        state.error = action.error.message;
        state.messages.push({
          role: "assistant",
          text: "⚠️ Something went wrong reaching the AI agent. Is the backend running and the Groq key set?",
          tools: [],
        });
      });
  },
});

export const { setDraft, clearDraft } = chatSlice.actions;
export default chatSlice.reducer;
