from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Feedback, User, WorkoutPlan


class DuplicateUserIdError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_user_by_user_id(db: Session, user_id: str) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.user_id == user_id)
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_pk: int) -> User | None:
    return db.get(User, user_pk)


def get_or_create_user(db: Session, *, user_id: str, name: str, age: int, weight: float, goal: str, intensity: str) -> User:
    existing = get_user_by_user_id(db, user_id)
    if existing:
        existing.name = name
        existing.age = age
        existing.weight = weight
        existing.goal = goal
        existing.intensity = intensity
        existing.updated_at = utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    user = User(user_id=user_id, name=name, age=age, weight=weight, goal=goal, intensity=intensity)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, *, name: str, age: int, weight: float, goal: str, intensity: str) -> User:
    user.name = name
    user.age = age
    user.weight = weight
    user.goal = goal
    user.intensity = intensity
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user(db: Session, *, user_id: str, name: str, age: int, weight: float, goal: str, intensity: str) -> User:
    if get_user_by_user_id(db, user_id):
        raise DuplicateUserIdError(f"User ID '{user_id}' already exists.")
    user = User(user_id=user_id, name=name, age=age, weight=weight, goal=goal, intensity=intensity)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    return list(db.scalars(stmt).all())


def count_users(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(User)) or 0)


def count_plans(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(WorkoutPlan)) or 0)


def count_updated_plans(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(WorkoutPlan).where(WorkoutPlan.version > 1)) or 0)


def get_plan_by_id(db: Session, plan_id: int) -> WorkoutPlan | None:
    return db.get(WorkoutPlan, plan_id)


def get_current_plan_for_user(db: Session, user: User) -> WorkoutPlan | None:
    stmt = (
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user.id, WorkoutPlan.is_current.is_(True))
        .order_by(WorkoutPlan.version.desc(), WorkoutPlan.created_at.desc())
    )
    return db.scalar(stmt)


def get_latest_plan_for_user(db: Session, user: User) -> WorkoutPlan | None:
    stmt = select(WorkoutPlan).where(WorkoutPlan.user_id == user.id).order_by(WorkoutPlan.version.desc(), WorkoutPlan.created_at.desc())
    return db.scalar(stmt)


def list_plans_for_user(db: Session, user: User) -> list[WorkoutPlan]:
    stmt = select(WorkoutPlan).where(WorkoutPlan.user_id == user.id).order_by(WorkoutPlan.version.desc(), WorkoutPlan.created_at.desc())
    return list(db.scalars(stmt).all())


def create_plan(db: Session, *, user: User, plan_data: dict, nutrition_tip: str, plan_type: str) -> WorkoutPlan:
    max_version = db.scalar(select(func.max(WorkoutPlan.version)).where(WorkoutPlan.user_id == user.id)) or 0
    if plan_type == "initial":
        max_version = 0 if max_version == 0 else max_version
    for existing in db.scalars(select(WorkoutPlan).where(WorkoutPlan.user_id == user.id, WorkoutPlan.is_current.is_(True))):
        existing.is_current = False
        db.add(existing)
    plan = WorkoutPlan(
        user_id=user.id,
        version=int(max_version) + 1,
        plan_type=plan_type,
        plan_data=plan_data,
        nutrition_tip=nutrition_tip,
        completion_state={"completed_days": []},
        is_current=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def create_feedback(db: Session, *, user: User, plan: WorkoutPlan, feedback_text: str) -> Feedback:
    feedback = Feedback(user_id=user.id, workout_plan_id=plan.id, feedback_text=feedback_text)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_for_plan(db: Session, plan: WorkoutPlan) -> list[Feedback]:
    stmt = select(Feedback).where(Feedback.workout_plan_id == plan.id).order_by(Feedback.created_at.desc())
    return list(db.scalars(stmt).all())


def get_history_with_feedback(db: Session, user: User) -> list[tuple[WorkoutPlan, Feedback | None]]:
    plans = list_plans_for_user(db, user)
    result: list[tuple[WorkoutPlan, Feedback | None]] = []
    for plan in plans:
        feedback = db.scalar(
            select(Feedback).where(Feedback.workout_plan_id == plan.id).order_by(Feedback.created_at.desc())
        )
        result.append((plan, feedback))
    return result


def list_recent_activity(db: Session, limit: int = 10) -> list[tuple[str, str, datetime]]:
    plans = list(db.scalars(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc()).limit(limit)).all())
    activity: list[tuple[str, str, datetime]] = []
    for plan in plans:
        activity.append(("plan", f"Plan v{plan.version} for user {plan.user_id}", plan.created_at))
    feedbacks = list(db.scalars(select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)).all())
    for feedback in feedbacks:
        activity.append(("feedback", f"Feedback for plan {feedback.workout_plan_id}", feedback.created_at))
    activity.sort(key=lambda item: item[2], reverse=True)
    return activity[:limit]
