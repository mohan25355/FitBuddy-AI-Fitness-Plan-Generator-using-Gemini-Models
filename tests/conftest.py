import os

import pytest

from app.core.security import hash_admin_password
from app.db.database import Base, engine


os.environ.setdefault("DATABASE_URL", "sqlite:///./fitbuddy_test.db")
os.environ.setdefault("GEMINI_API_KEY", "test-api-key")
os.environ.setdefault("GEMINI_WORKOUT_MODEL", "gemini-test-workout")
os.environ.setdefault("GEMINI_FAST_MODEL", "gemini-test-fast")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", hash_admin_password("adminpass"))
os.environ.setdefault("SECRET_KEY", "test-secret-key")


@pytest.fixture(autouse=True)
def reset_database():
	Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)
	yield
