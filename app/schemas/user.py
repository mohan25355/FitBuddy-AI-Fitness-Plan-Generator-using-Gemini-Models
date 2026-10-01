from pydantic import BaseModel, Field, field_validator


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    user_id: str = Field(min_length=3, max_length=80)
    age: int = Field(ge=10, le=100)
    weight: float = Field(gt=0, le=500)
    goal: str = Field(min_length=1, max_length=40)
    intensity: str = Field(min_length=1, max_length=20)

    @field_validator("name", "user_id", "goal", "intensity")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        return value.strip()


class UserOut(BaseModel):
    id: int
    user_id: str
    name: str
    age: int
    weight: float
    goal: str
    intensity: str
    created_at: str
    updated_at: str