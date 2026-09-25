import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import ai_routes, auth_routes, post_routes, project_routes
from db.session import init_db
from routes import auth_routes

# Ensure local media directory exists on host startup
MEDIA_DIR = os.getenv("MEDIA_DIR", "uploads")
os.makedirs(MEDIA_DIR, exist_ok=True)

init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="DevSocial API",
    version="1.0.0",
    description="Backend service for DevSocial media platform",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded media files locally
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Register API routes
app.include_router(auth_routes.router)
app.include_router(project_routes.router)
app.include_router(auth_routes.router)
app.include_router(project_routes.router)
app.include_router(post_routes.router)
app.include_router(auth_routes.router)
app.include_router(project_routes.router)
app.include_router(post_routes.router)
app.include_router(ai_routes.router)

@app.get("/")
def health_check():
    return {"status": "online", "message": "DevSocial Backend System Operational"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)