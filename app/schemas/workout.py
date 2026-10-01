from pydantic import BaseModel, Field, field_validator, model_validator


class WorkoutExercise(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sets: int = Field(ge=0, le=20)
    reps: int | str | None = Field(default=None)
    duration_minutes: int | str | None = Field(default=None)
    rest_seconds: int | str = Field(default=60)
    notes: str = Field(default="", max_length=240)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, value):
        if isinstance(value, dict):
            data = dict(value)
            if "rest_seconds" not in data and "rest" in data:
                data["rest_seconds"] = data.pop("rest")
            if "rest_seconds" not in data and "interval" in data:
                data["rest_seconds"] = data.pop("interval")
            if "duration_minutes" not in data and "duration" in data:
                data["duration_minutes"] = data.pop("duration")
            return data
        return value


class WorkoutDay(BaseModel):
    day: int = Field(ge=1, le=7)
    focus: str = Field(min_length=1, max_length=80)
    warmup: list[str] = Field(min_length=1)
    exercises: list[WorkoutExercise] = Field(min_length=1)
    cooldown: list[str] = Field(min_length=1)
    recovery_tip: str = Field(default="Hydrate well, sleep 7-8 hours, and keep recovery active.", max_length=240)

    @model_validator(mode="before")
    @classmethod
    def normalize_day(cls, value):
        if isinstance(value, dict):
            data = dict(value)
            if isinstance(data.get("warmup"), str):
                data["warmup"] = [item.strip() for item in data["warmup"].replace(" and ", ",").split(",") if item.strip()]
            if isinstance(data.get("cooldown"), str):
                data["cooldown"] = [item.strip() for item in data["cooldown"].replace(" and ", ",").split(",") if item.strip()]
            if "recovery_tip" not in data:
                data["recovery_tip"] = data.get("tip") or data.get("recovery") or "Hydrate well, sleep 7-8 hours, and keep recovery active."
            return data
        return value


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