from __future__ import annotations

from app.core.config import Settings
from app.schemas.ai import AIPlanOnlyPayload
from app.schemas.user import UserInput
from app.schemas.workout import WorkoutPlanData
from app.services.gemini_service import GeminiService


class WorkoutService:
    def __init__(self, settings: Settings, gemini_service: GeminiService):
        self.settings = settings
        self.gemini = gemini_service

    def _workout_prompt(self, user: UserInput, context: str) -> str:
        return (
            "You are an expert fitness coach. Return valid JSON only. "
            "Create a safe, realistic, personalized 7-day workout plan. "
            "Never add medical claims or unsafe instructions. "
            "Use exactly 7 days and provide warmup, exercises, sets, repetitions or duration, rest intervals, cooldown, and recovery guidance. "
            "The structure must be: {\"plan\": {\"title\": ..., \"goal\": ..., \"intensity\": ..., \"days\": [...]}}. "
            f"User profile: name={user.name}, user_id={user.user_id}, age={user.age}, weight={user.weight}, goal={user.goal}, intensity={user.intensity}. "
            f"{context}"
        )

    def generate_plan(self, user: UserInput) -> WorkoutPlanData:
        payload = self.gemini.generate_structured(
            model=self.settings.default_workout_model,
            prompt=self._workout_prompt(user, "Focus on fitness guidance appropriate for the supplied goal and intensity."),
            schema=AIPlanOnlyPayload,
        )
        return payload.plan

    def adapt_plan(self, user: UserInput, existing_plan: dict, feedback_text: str) -> WorkoutPlanData:
        payload = self.gemini.generate_structured(
            model=self.settings.default_workout_model,
            prompt=self._workout_prompt(
                user,
                "Adapt the current plan using the user feedback while keeping useful safe elements. "
                f"Current plan JSON: {existing_plan}. Feedback: {feedback_text}."
            ),
            schema=AIPlanOnlyPayload,
        )
        return payload.plan