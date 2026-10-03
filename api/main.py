from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Black Box API", description="API for Black Box Agent Flight Recorder")
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Black Box API is running"}
