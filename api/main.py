from contextlib import asynccontextmanager
from fastapi import FastAPI
from storage.database import init_db
from .routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Black Box API", description="API for Black Box Agent Flight Recorder", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

