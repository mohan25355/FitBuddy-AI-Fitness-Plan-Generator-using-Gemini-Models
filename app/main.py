from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
import json

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, logger
from app.core.security import generate_csrf_token, hash_admin_password, session_token, verify_admin_password, verify_session_token
from app.db.database import get_db, init_db
from app.db.repositories import (
    DuplicateUserIdError,
    NotFoundError,
    count_plans,
    count_updated_plans,
    count_users,
    create_feedback,
    create_plan,
    create_user,
    get_or_create_user,
    get_current_plan_for_user,
    get_history_with_feedback,
    get_latest_plan_for_user,
    get_plan_by_id,
    get_user_by_user_id,
    list_recent_activity,
    list_users,
)
from app.schemas.feedback import FeedbackRequest
from app.schemas.user import UserInput
from app.schemas.workout import WorkoutPlanData
from app.services.feedback_service import FeedbackService
from app.services.gemini_service import GeminiService, GeminiServiceError
from app.services.nutrition_service import NutritionService
from app.services.workout_service import WorkoutService


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    init_db()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=app_lifespan,
    )
    app.state.settings = settings
    app.state.gemini_service = GeminiService(settings)
    app.state.workout_service = WorkoutService(settings, app.state.gemini_service)
    app.state.nutrition_service = NutritionService(settings, app.state.gemini_service)
    app.state.feedback_service = FeedbackService(settings, app.state.gemini_service)

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie=settings.session_cookie_name, same_site="lax", https_only=False)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(status_code=422, content={"detail": "Invalid request data."})
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Validation Error", "message": "Please review the form fields and try again."},
            status_code=422,
        )

    @app.exception_handler(GeminiServiceError)
    async def gemini_exception_handler(request: Request, exc: GeminiServiceError):
        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(status_code=503, content={"detail": str(exc)})
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "AI Service Unavailable", "message": str(exc)},
            status_code=503,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled application error")
        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Unexpected Error", "message": "Something went wrong. Please try again."},
            status_code=500,
        )

    def ensure_csrf(request: Request) -> str:
        token = request.session.get("csrf_token")
        if not token:
            token = generate_csrf_token()
            request.session["csrf_token"] = token
        return token

    def verify_csrf(request: Request, csrf_token: str | None) -> None:
        expected = request.session.get("csrf_token")
        if not expected or not csrf_token or csrf_token != expected:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")

    def get_templates_context(request: Request, **kwargs):
        return {"request": request, "csrf_token": ensure_csrf(request), **kwargs}

    def serialize_user(user):
        return {
            "id": user.id,
            "user_id": user.user_id,
            "name": user.name,
            "age": user.age,
            "weight": float(user.weight),
            "goal": user.goal,
            "intensity": user.intensity,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    def serialize_plan(plan):
        nutrition_tip = plan.nutrition_tip
        try:
            nutrition_tip = json.loads(nutrition_tip) if isinstance(nutrition_tip, str) else nutrition_tip
        except Exception:
            nutrition_tip = {"tip": plan.nutrition_tip, "why_it_matters": "", "practical_action": ""}
        return {
            "id": plan.id,
            "user_id": plan.user_id,
            "version": plan.version,
            "plan_type": plan.plan_type,
            "plan_data": plan.plan_data,
            "nutrition_tip": nutrition_tip,
            "completion_state": plan.completion_state,
            "is_current": plan.is_current,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
        }

    def get_user_or_404(db: Session, user_id: str):
        user = get_user_by_user_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    def get_plan_or_404(db: Session, plan_id: int):
        plan = get_plan_by_id(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        return plan

    def render_dashboard(request: Request, db: Session, user_id: str, message: str | None = None):
        user = get_user_or_404(db, user_id)
        current_plan = get_current_plan_for_user(db, user)
        history = get_history_with_feedback(db, user)
        latest_plan = get_latest_plan_for_user(db, user)
        completed_count = len((current_plan.completion_state or {}).get("completed_days", [])) if current_plan else 0
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            get_templates_context(
                request,
                title=f"FitBuddy - {user.name}",
                user=serialize_user(user),
                current_plan=serialize_plan(current_plan) if current_plan else None,
                latest_plan=serialize_plan(latest_plan) if latest_plan else None,
                history=[{"plan": serialize_plan(plan), "feedback": feedback.feedback_text if feedback else None} for plan, feedback in history],
                completed_count=completed_count,
                total_count=7,
                message=message,
            ),
        )

    @app.get("/feedback/{user_id}", response_class=HTMLResponse, tags=["Feedback"])
    def feedback_page(request: Request, user_id: str, db: Session = Depends(get_db)):
        user = get_user_or_404(db, user_id)
        return templates.TemplateResponse(
            request,
            "feedback.html",
            get_templates_context(request, title="Feedback - FitBuddy", user=serialize_user(user)),
        )

    @app.get("/", response_class=HTMLResponse, tags=["Health"])
    def home(request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            get_templates_context(request, title="FitBuddy - AI Fitness Plan Generator"),
        )

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    @app.get("/onboarding", response_class=HTMLResponse, tags=["Users"])
    def onboarding(request: Request):
        return templates.TemplateResponse(
            request,
            "onboarding.html",
            get_templates_context(request, title="Get Started - FitBuddy"),
        )

    @app.post("/generate-workout", response_class=HTMLResponse, tags=["Workouts"])
    def generate_workout(
        request: Request,
        name: str = Form(...),
        user_id: str = Form(...),
        age: int = Form(...),
        weight: float = Form(...),
        goal: str = Form(...),
        intensity: str = Form(...),
        csrf_token: str = Form(...),
        db: Session = Depends(get_db),
    ):
        verify_csrf(request, csrf_token)
        profile = UserInput(name=name, user_id=user_id, age=age, weight=weight, goal=goal, intensity=intensity)
        user = get_or_create_user(db, **profile.model_dump())
        workout_service: WorkoutService = request.app.state.workout_service
        nutrition_service: NutritionService = request.app.state.nutrition_service
        plan_data = workout_service.generate_plan(profile)
        nutrition_tip = nutrition_service.generate_tip(profile)
        plan = create_plan(db, user=user, plan_data=plan_data.model_dump(), nutrition_tip=nutrition_tip.model_dump_json(), plan_type="initial")
        response = RedirectResponse(url=f"/dashboard/{user.user_id}", status_code=303)
        response.set_cookie("fitbuddy_last_user", user.user_id, httponly=False, samesite="lax")
        return response

    @app.post("/api/workouts/generate", tags=["Workouts"])
    def api_generate_workout(
        payload: UserInput,
        db: Session = Depends(get_db),
    ):
        user = get_or_create_user(db, **payload.model_dump())
        workout_service: WorkoutService = app.state.workout_service
        nutrition_service: NutritionService = app.state.nutrition_service
        plan_data = workout_service.generate_plan(payload)
        nutrition_tip = nutrition_service.generate_tip(payload)
        plan = create_plan(db, user=user, plan_data=plan_data.model_dump(), nutrition_tip=nutrition_tip.model_dump_json(), plan_type="initial")
        return {"user": serialize_user(user), "plan": serialize_plan(plan)}

    @app.get("/dashboard/{user_id}", response_class=HTMLResponse, tags=["Users"])
    def dashboard(request: Request, user_id: str, db: Session = Depends(get_db)):
        return render_dashboard(request, db, user_id)

    @app.get("/workout/{plan_id}", response_class=HTMLResponse, tags=["Workouts"])
    def workout_detail(request: Request, plan_id: int, db: Session = Depends(get_db)):
        plan = get_plan_or_404(db, plan_id)
        user = plan.user
        return templates.TemplateResponse(
            request,
            "workout.html",
            get_templates_context(
                request,
                title=f"Workout Plan v{plan.version} - FitBuddy",
                user=serialize_user(user),
                current_plan=serialize_plan(plan),
                completed_count=len((plan.completion_state or {}).get("completed_days", [])),
                total_count=7,
            ),
        )

    @app.get("/history/{user_id}", response_class=HTMLResponse, tags=["Users"])
    def history(request: Request, user_id: str, db: Session = Depends(get_db)):
        user = get_user_or_404(db, user_id)
        history_items = get_history_with_feedback(db, user)
        return templates.TemplateResponse(
            request,
            "history.html",
            get_templates_context(request, title="Plan History - FitBuddy", user=serialize_user(user), history=[{"plan": serialize_plan(plan), "feedback": feedback.feedback_text if feedback else None} for plan, feedback in history_items]),
        )

    @app.post("/submit-feedback", response_class=HTMLResponse, tags=["Feedback"])
    def submit_feedback(
        request: Request,
        user_id: str = Form(...),
        feedback_text: str = Form(...),
        csrf_token: str = Form(...),
        db: Session = Depends(get_db),
    ):
        verify_csrf(request, csrf_token)
        user = get_user_or_404(db, user_id)
        current_plan = get_current_plan_for_user(db, user)
        if not current_plan:
            raise HTTPException(status_code=404, detail="No plan found for user.")
        feedback_service: FeedbackService = request.app.state.feedback_service
        feedback_text = feedback_service.validate_feedback(feedback_text)
        feedback = create_feedback(db, user=user, plan=current_plan, feedback_text=feedback_text)
        adapted_plan_data = feedback_service.adapt_plan(user=UserInput(name=user.name, user_id=user.user_id, age=user.age, weight=float(user.weight), goal=user.goal, intensity=user.intensity), current_plan=WorkoutPlanData.model_validate(current_plan.plan_data), feedback=FeedbackRequest(user_id=user.user_id, feedback_text=feedback_text))
        plan = create_plan(db, user=user, plan_data=adapted_plan_data.model_dump(), nutrition_tip=current_plan.nutrition_tip, plan_type="adapted")
        return render_dashboard(request, db, user.user_id, message="Your plan has been updated.")

    @app.post("/api/workouts/{plan_id}/adapt", tags=["Workouts"])
    def api_adapt_plan(plan_id: int, payload: FeedbackRequest, db: Session = Depends(get_db)):
        user = get_user_or_404(db, payload.user_id)
        current_plan = get_plan_or_404(db, plan_id)
        if current_plan.user_id != user.id:
            raise HTTPException(status_code=403, detail="Plan does not belong to the specified user.")
        feedback_service: FeedbackService = app.state.feedback_service
        feedback_text = feedback_service.validate_feedback(payload.feedback_text)
        create_feedback(db, user=user, plan=current_plan, feedback_text=feedback_text)
        adapted_plan = feedback_service.adapt_plan(user=UserInput(name=user.name, user_id=user.user_id, age=user.age, weight=float(user.weight), goal=user.goal, intensity=user.intensity), current_plan=WorkoutPlanData.model_validate(current_plan.plan_data), feedback=payload)
        new_plan = create_plan(db, user=user, plan_data=adapted_plan.model_dump(), nutrition_tip=current_plan.nutrition_tip, plan_type="adapted")
        return {"user": serialize_user(user), "plan": serialize_plan(new_plan)}

    @app.get("/view-all-users", response_class=HTMLResponse, tags=["Admin"])
    def view_all_users(request: Request, db: Session = Depends(get_db)):
        if not request.session.get("admin_authenticated"):
            return RedirectResponse(url="/admin/login", status_code=303)
        users = list_users(db)
        return templates.TemplateResponse(
            request,
            "admin.html",
            get_templates_context(
                request,
                title="Admin Dashboard - FitBuddy",
                total_users=count_users(db),
                total_plans=count_plans(db),
                updated_plans=count_updated_plans(db),
                recent_activity=[{"kind": kind, "label": label, "created_at": created_at.isoformat()} for kind, label, created_at in list_recent_activity(db)],
                users=[serialize_user(user) for user in users],
                admin_mode=True,
            ),
        )

    @app.get("/admin/login", response_class=HTMLResponse, tags=["Admin"])
    def admin_login(request: Request):
        return templates.TemplateResponse(request, "admin.html", get_templates_context(request, title="Admin Login - FitBuddy", login_only=True))

    @app.post("/admin/login", tags=["Admin"])
    def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
        verify_csrf(request, csrf_token)
        if username != settings.admin_username or not verify_admin_password(password, settings.admin_password_hash):
            raise HTTPException(status_code=401, detail="Invalid admin credentials.")
        request.session["admin_authenticated"] = True
        request.session["admin_username"] = username
        request.session["admin_token"] = session_token(username, settings.secret_key)
        return RedirectResponse(url="/view-all-users", status_code=303)

    @app.post("/admin/logout", tags=["Admin"])
    def admin_logout(request: Request, csrf_token: str = Form(...)):
        verify_csrf(request, csrf_token)
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    @app.get("/api/users/{user_id}", tags=["Users"])
    def api_get_user(user_id: str, db: Session = Depends(get_db)):
        user = get_user_or_404(db, user_id)
        return {"user": serialize_user(user)}

    @app.get("/api/users/{user_id}/history", tags=["Users"])
    def api_get_history(user_id: str, db: Session = Depends(get_db)):
        user = get_user_or_404(db, user_id)
        history_items = get_history_with_feedback(db, user)
        return {"history": [{"plan": serialize_plan(plan), "feedback": feedback.feedback_text if feedback else None} for plan, feedback in history_items]}

    @app.get("/api/admin/users", tags=["Admin"])
    def api_admin_users(request: Request, db: Session = Depends(get_db)):
        if not request.session.get("admin_authenticated"):
            raise HTTPException(status_code=403, detail="Admin access required.")
        return {"users": [serialize_user(user) for user in list_users(db)]}

    return app


app = create_app()
