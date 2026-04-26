from fastapi import FastAPI

app = FastAPI(
    title="SmartMatch Pro API",
    description="Backend intelligent pour analyse d'offres, matching et recommandation",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "SmartMatch Pro Backend is running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }