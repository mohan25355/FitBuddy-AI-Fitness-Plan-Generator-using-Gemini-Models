from pydantic import BaseModel

from pydantic import model_validator

from app.schemas.workout import NutritionTip, WorkoutPlanData


class AIGenerationPayload(BaseModel):
    plan: WorkoutPlanData
    nutrition_tip: NutritionTip


class AIPlanOnlyPayload(BaseModel):
    plan: WorkoutPlanData


class AIUpdateResponse(BaseModel):
    plan: WorkoutPlanData


class AIPlanFlexiblePayload(BaseModel):
    plan: WorkoutPlanData

    @model_validator(mode="before")
    @classmethod
    def wrap_direct_plan(cls, value):
        if isinstance(value, dict) and "plan" not in value and "days" in value and "title" in value:
            return {"plan": value}
        return value