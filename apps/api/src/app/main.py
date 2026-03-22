from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routes import auth, sessions, settings
from app.schema_upgrades import apply_startup_schema_upgrades

app = FastAPI(title="Speech-Machine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    apply_startup_schema_upgrades()


app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(settings.router)
