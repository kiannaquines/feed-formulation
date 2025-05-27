from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import *
from models.models import *

from routes.authentication_routes import auth_router
from routes.chicken_feed_formulation_routes import chicken_feed_formulation_router
from routes.root_routes import root_router

init_database()

app = FastAPI(
    title="Feed Formulation API with Authentication",
    description="API for feed formulation and management with user authentication and OTP security",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chicken_feed_formulation_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)