
from datetime import timedelta
from typing import Optional

import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import SessionLocal, ItemModel, UserModel
from app.security import (
    oauth2_scheme,
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ItemResponse(ItemCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        username = payload.get("sub")

        if not isinstance(username, str) or not username:
            raise credentials_error

    except InvalidTokenError:
        raise credentials_error

    user = db.query(UserModel).filter(
        UserModel.username == username
    ).first()

    if user is None:
        raise credentials_error

    return user


@app.get("/")
def home():
    return {"message": "Hello World! FastAPI is working."}


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.query(UserModel).filter(
        UserModel.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )

    new_user = UserModel(
        username=user.username,
        hashed_password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.post("/auth/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(
        UserModel.username == form_data.username
    ).first()

    if user is None or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    new_item = ItemModel(
        name=item.name,
        description=item.description,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/items", response_model=list[ItemResponse])
def get_items(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(ItemModel).all()


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ItemModel).filter(
        ItemModel.id == item_id
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    updated_item: ItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ItemModel).filter(
        ItemModel.id == item_id
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    item.name = updated_item.name
    item.description = updated_item.description

    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ItemModel).filter(
        ItemModel.id == item_id
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item deleted successfully"}
