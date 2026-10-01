from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=3, max_length=80)
    feedback_text: str = Field(min_length=3, max_length=1000)


class FeedbackOut(BaseModel):
    id: int
    user_id: int
    workout_plan_id: int
    feedback_text: str
    created_at: str