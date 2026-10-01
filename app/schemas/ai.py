from pydantic import BaseModel

from app.schemas.workout import NutritionTip, WorkoutPlanData


class AIGenerationPayload(BaseModel):
    plan: WorkoutPlanData
    nutrition_tip: NutritionTip


class AIPlanOnlyPayload(BaseModel):
    plan: WorkoutPlanData


class AIUpdateResponse(BaseModel):
    plan: WorkoutPlanData