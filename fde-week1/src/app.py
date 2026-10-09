from fastapi import FastAPI
app = FastAPI(title="FDE Week 1 API")
@app.get("/health")
def health():
 return {"status": "ready", "week": 1}