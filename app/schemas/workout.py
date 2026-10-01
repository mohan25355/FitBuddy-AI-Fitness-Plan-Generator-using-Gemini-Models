from pydantic import BaseModel, Field, field_validator


class WorkoutExercise(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sets: int = Field(ge=0, le=20)
    reps: int | None = Field(default=None, ge=0, le=100)
    duration_minutes: int | None = Field(default=None, ge=0, le=180)
    rest_seconds: int = Field(ge=0, le=600)
    notes: str = Field(default="", max_length=240)


class WorkoutDay(BaseModel):
    day: int = Field(ge=1, le=7)
    focus: str = Field(min_length=1, max_length=80)
    warmup: list[str] = Field(min_length=1)
    exercises: list[WorkoutExercise] = Field(min_length=1)
    cooldown: list[str] = Field(min_length=1)
    recovery_tip: str = Field(min_length=1, max_length=240)


class WorkoutPlanData(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=40)
    intensity: str = Field(min_length=1, max_length=20)
    days: list[WorkoutDay]

    @field_validator("days")
    @classmethod
    def validate_exactly_seven_days(cls, value: list[WorkoutDay]) -> list[WorkoutDay]:
        if len(value) != 7:
            raise ValueError("Workout plan must contain exactly 7 days")
        expected_days = list(range(1, 8))
        actual_days = [day.day for day in value]
        if actual_days != expected_days:
            raise ValueError("Workout plan days must be numbered 1 through 7 in order")
        return value


class NutritionTip(BaseModel):
    tip: str = Field(min_length=1, max_length=240)
    why_it_matters: str = Field(min_length=1, max_length=240)
    practical_action: str = Field(min_length=1, max_length=240)


class WorkoutPlanResponse(BaseModel):
    plan: WorkoutPlanData
    nutrition_tip: NutritionTip


class AIWorkoutResponse(BaseModel):
    plan: WorkoutPlanData


class AIUpdateResponse(BaseModel):
    plan: WorkoutPlanData