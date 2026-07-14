import { createSlice } from "@reduxjs/toolkit";
import { sendMessage } from "./chatSlice";

export const EMPTY_FORM = {
  id: null,
  hcp_name: "",
  interaction_type: "",
  date: "",
  time: "",
  attendees: "",
  topics_discussed: "",
  materials_shared: "",
  samples_distributed: "",
  sentiment: "",
  outcomes: "",
  follow_up_actions: "",
  ai_suggested_followups: [],
};

// Which fields changed on the last agent turn -> used to briefly highlight them,
// visually proving the AI (not the user) filled the form.
function diffFields(prev, next) {
  const changed = [];
  for (const key of Object.keys(EMPTY_FORM)) {
    if (key === "ai_suggested_followups") continue;
    if ((prev[key] || "") !== (next[key] || "")) changed.push(key);
  }
  return changed;
}

const formSlice = createSlice({
  name: "form",
  initialState: {
    data: { ...EMPTY_FORM },
    flashFields: [],
  },
  reducers: {
    clearFlash(state) {
      state.flashFields = [];
    },
  },
  extraReducers: (builder) => {
    // The form is ONLY ever updated by the AI agent's response — never by
    // manual typing. This is the core requirement of the assignment.
    builder.addCase(sendMessage.fulfilled, (state, action) => {
      const next = { ...EMPTY_FORM, ...action.payload.form_data };
      state.flashFields = diffFields(state.data, next);
      state.data = next;
    });
  },
});

export const { clearFlash } = formSlice.actions;
export default formSlice.reducer;
