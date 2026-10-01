from __future__ import annotations

from app.core.config import Settings
from app.schemas.ai import AIPlanFlexiblePayload
from app.schemas.feedback import FeedbackRequest
from app.schemas.user import UserInput
from app.schemas.workout import WorkoutPlanData
from app.services.gemini_service import GeminiService


class FeedbackService:
    def __init__(self, settings: Settings, gemini_service: GeminiService):
        self.settings = settings
        self.gemini = gemini_service

    def validate_feedback(self, feedback_text: str) -> str:
        cleaned = feedback_text.strip()
        if len(cleaned) < 3:
            raise ValueError("Feedback must be at least 3 characters long.")
        if len(cleaned) > 1000:
            raise ValueError("Feedback must be 1000 characters or fewer.")
        return cleaned

    def adapt_plan(self, user: UserInput, current_plan: WorkoutPlanData, feedback: FeedbackRequest) -> WorkoutPlanData:
        prompt = (
            "You are a cautious fitness coach. Return valid JSON only for a 7-day plan. "
            "Follow the user's feedback when safe, but do not recommend unsafe or extreme training. "
            "Preserve useful parts of the existing plan when possible. "
            f"User profile: name={user.name}, age={user.age}, weight={user.weight}, goal={user.goal}, intensity={user.intensity}. "
            f"Current plan JSON: {current_plan.model_dump()}. Feedback: {feedback.feedback_text}."
        )
        payload = self.gemini.generate_structured(
            model=self.settings.default_workout_model,
            prompt=prompt,
            schema=AIPlanFlexiblePayload,
        )
        return payload.plan