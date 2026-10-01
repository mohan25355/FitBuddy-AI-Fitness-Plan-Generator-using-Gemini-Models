from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_admin_password
from app.db.database import Base, engine, SessionLocal
from app.db.models import Feedback, User, WorkoutPlan
from app.db.repositories import DuplicateUserIdError, create_user
from app.main import create_app
from app.schemas.user import UserInput
from app.schemas.workout import NutritionTip, WorkoutDay, WorkoutExercise, WorkoutPlanData
from app.services.gemini_service import GeminiService, GeminiServiceError


@pytest.fixture()
def app():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    application = create_app()
    application.state.gemini_service = GeminiService(application.state.settings)
    return application


@pytest.fixture()
def client(app):
    return TestClient(app)


def sample_plan() -> dict:
    days = []
    for day in range(1, 8):
        days.append(
            {
                "day": day,
                "focus": f"Focus {day}",
                "warmup": ["5 min walk"],
                "exercises": [
                    {
                        "name": f"Exercise {day}",
                        "sets": 3,
                        "reps": 10,
                        "duration_minutes": None,
                        "rest_seconds": 60,
                        "notes": "Controlled tempo",
                    }
                ],
                "cooldown": ["Breathing"],
                "recovery_tip": "Hydrate and rest",
            }
        )
    return {
        "title": "Test Plan",
        "goal": "Weight Loss",
        "intensity": "Medium",
        "days": days,
    }


def sample_nutrition() -> dict:
    return {
        "tip": "Keep protein steady.",
        "why_it_matters": "Supports recovery.",
        "practical_action": "Add protein to each meal.",
    }


def patch_generation(app, plan_overrides: list[dict] | None = None):
    plans = plan_overrides or [sample_plan()]

    def generate_plan(_profile):
        return WorkoutPlanData.model_validate(plans.pop(0))

    def generate_tip(_profile):
        return NutritionTip.model_validate(sample_nutrition())

    def adapt_plan(*, user, current_plan, feedback):
        return WorkoutPlanData.model_validate(sample_plan())

    app.state.workout_service.generate_plan = generate_plan
    app.state.nutrition_service.generate_tip = generate_tip
    app.state.feedback_service.adapt_plan = adapt_plan


def extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found in HTML"
    return match.group(1)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_user_validation_rejects_invalid_age():
    with pytest.raises(Exception):
        UserInput(name="A", user_id="user-1", age=3, weight=70, goal="Weight Loss", intensity="Low")


def test_duplicate_user_id_raises():
    db = SessionLocal()
    try:
        create_user(db, user_id="user-dup", name="One", age=30, weight=70, goal="Weight Loss", intensity="Medium")
        with pytest.raises(DuplicateUserIdError):
            create_user(db, user_id="user-dup", name="Two", age=31, weight=72, goal="Muscle Gain", intensity="High")
    finally:
        db.close()


def test_generate_workout_creates_plan(client, app):
    patch_generation(app)
    onboarding = client.get("/onboarding")
    csrf_token = extract_csrf_token(onboarding.text)
    response = client.post(
        "/generate-workout",
        data={
            "csrf_token": csrf_token,
            "name": "Alex",
            "user_id": "alex-001",
            "age": 29,
            "weight": 72.5,
            "goal": "Weight Loss",
            "intensity": "Medium",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == "alex-001").one()
        plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).all()
        assert len(plans) == 1
        assert len(plans[0].plan_data["days"]) == 7
    finally:
        db.close()


def test_feedback_adaptation_preserves_history(client, app):
    patch_generation(app, plan_overrides=[sample_plan(), sample_plan()])
    onboarding = client.get("/onboarding")
    csrf_token = extract_csrf_token(onboarding.text)
    response = client.post(
        "/generate-workout",
        data={
            "csrf_token": csrf_token,
            "name": "Alex",
            "user_id": "alex-002",
            "age": 29,
            "weight": 72.5,
            "goal": "Weight Loss",
            "intensity": "Medium",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    dashboard = client.get("/dashboard/alex-002")
    feedback_token = extract_csrf_token(dashboard.text)
    response = client.post(
        "/submit-feedback",
        data={
            "csrf_token": feedback_token,
            "user_id": "alex-002",
            "feedback_text": "Add more cardio and one rest day.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == "alex-002").one()
        plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).order_by(WorkoutPlan.version.asc()).all()
        feedbacks = db.query(Feedback).filter(Feedback.user_id == user.id).all()
        assert len(plans) == 2
        assert plans[0].version == 1
        assert plans[1].version == 2
        assert len(feedbacks) == 1
        assert plans[0].is_current is False
        assert plans[1].is_current is True
    finally:
        db.close()


def test_admin_auth_and_dashboard(client, app):
    patch_generation(app)
    app.state.settings.admin_password_hash = hash_admin_password("adminpass")
    login_page = client.get("/admin/login")
    csrf_token = extract_csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={"csrf_token": csrf_token, "username": "admin", "password": "adminpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.get("/view-all-users")
    assert response.status_code == 200


def test_gemini_service_without_key_raises():
    service = GeminiService(type("SettingsLike", (), {"gemini_api_key": "", "default_fast_model": "fast", "default_workout_model": "workout"})())
    with pytest.raises(GeminiServiceError):
        service.generate_structured(model="workout", prompt="{}", schema=NutritionTip)
