from contextlib import asynccontextmanager
from fastapi import FastAPI
from storage.database import init_db
from .routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "https://bnb-26-no-sleep-club-internal-round.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app = FastAPI(title="Black Box API", description="API for Black Box Agent Flight Recorder", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Black Box API is running"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "blackbox-api"}

