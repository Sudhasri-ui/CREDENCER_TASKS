from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello World"}

@app.get("/status")
def status():
    return {"status": "success", "code": 200}
@app.get("/items/{item_id}")
def get_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query": q, "status": "active"}
