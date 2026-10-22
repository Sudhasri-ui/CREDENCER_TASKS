
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import SessionLocal, ItemModel

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ItemResponse(ItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


@app.get("/")
def home():
    return {"message": "Hello World! FastAPI is working."}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = ItemModel(
        name=item.name,
        description=item.description,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/items", response_model=list[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    return db.query(ItemModel).all()


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    updated_item: ItemCreate,
    db: Session = Depends(get_db),
):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    item.name = updated_item.name
    item.description = updated_item.description

    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item deleted successfully"}
