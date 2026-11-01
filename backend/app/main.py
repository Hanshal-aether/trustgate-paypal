from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import signup, login, dashboard, demo, ml, paypal

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TrustGate API",
    description="Account-integrity layer: signup fraud risk scoring + household/session abuse detection.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo-only; restrict in real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signup.router)
app.include_router(login.router)
app.include_router(dashboard.router)
app.include_router(demo.router)
app.include_router(ml.router)
app.include_router(paypal.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "TrustGate API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
