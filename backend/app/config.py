import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change_me")
ALGORITHM = "HS256"
