from app.schemas.workout import WorkoutDay, WorkoutExercise, WorkoutPlanData


def test_workout_plan_requires_seven_days():
    days = []
    for day in range(1, 8):
        days.append(
            {
                "day": day,
                "focus": "Strength",
                "warmup": ["Walk"],
                "exercises": [{"name": "Squat", "sets": 3, "reps": 10, "duration_minutes": None, "rest_seconds": 60, "notes": ""}],
                "cooldown": ["Stretch"],
                "recovery_tip": "Rest well",
            }
        )
    plan = WorkoutPlanData.model_validate({"title": "Plan", "goal": "Wellness", "intensity": "Low", "days": days})
    assert len(plan.days) == 7
