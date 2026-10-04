from fastapi import FastAPI

app = FastAPI(
    title="Emergency Response Platform API",
    version="0.1.0",
    description="Emergency Response Platform Backend API (Initial Setup)",
)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Emergency Response Platform API",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
