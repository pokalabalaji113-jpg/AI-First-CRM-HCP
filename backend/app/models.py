"""Database model for a logged HCP interaction."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    # Fields mirror the "Log Interaction Screen" from the assignment.
    hcp_name = Column(String(255), default="")
    interaction_type = Column(String(100), default="")
    date = Column(String(50), default="")
    time = Column(String(50), default="")
    attendees = Column(Text, default="")
    topics_discussed = Column(Text, default="")
    materials_shared = Column(Text, default="")
    samples_distributed = Column(Text, default="")
    sentiment = Column(String(50), default="")
    outcomes = Column(Text, default="")
    follow_up_actions = Column(Text, default="")
    ai_suggested_followups = Column(Text, default="")  # newline-separated

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_form(self) -> dict:
        """Serialize to the flat dict the frontend form/Redux uses."""
        return {
            "id": self.id,
            "hcp_name": self.hcp_name or "",
            "interaction_type": self.interaction_type or "",
            "date": self.date or "",
            "time": self.time or "",
            "attendees": self.attendees or "",
            "topics_discussed": self.topics_discussed or "",
            "materials_shared": self.materials_shared or "",
            "samples_distributed": self.samples_distributed or "",
            "sentiment": self.sentiment or "",
            "outcomes": self.outcomes or "",
            "follow_up_actions": self.follow_up_actions or "",
            "ai_suggested_followups": [
                s for s in (self.ai_suggested_followups or "").split("\n") if s.strip()
            ],
        }
