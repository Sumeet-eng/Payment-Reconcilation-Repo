from fastapi import FastAPI

from app.routers import reconcile

app = FastAPI(
    title="Payment Reconciliation System",
    description="Upload an internal ledger CSV and a bank statement CSV; get back what matches and what doesn't.",
    version="1.0.0",
)

app.include_router(reconcile.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
