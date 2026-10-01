from __future__ import annotations

from app.core.config import Settings
from app.schemas.user import UserInput
from app.schemas.workout import NutritionTip
from app.services.gemini_service import GeminiService


class NutritionService:
    def __init__(self, settings: Settings, gemini_service: GeminiService):
        self.settings = settings
        self.gemini = gemini_service

    def generate_tip(self, user: UserInput) -> NutritionTip:
        prompt = (
            "You are a concise fitness nutrition assistant. Return valid JSON only with fields tip, why_it_matters, and practical_action. "
            "Keep the advice general, safe, and non-medical. Avoid extreme dieting and medication advice. "
            f"User profile: age={user.age}, weight={user.weight}, goal={user.goal}, intensity={user.intensity}."
        )
        return self.gemini.generate_structured(
            model=self.settings.default_fast_model,
            prompt=prompt,
            schema=NutritionTip,
        )