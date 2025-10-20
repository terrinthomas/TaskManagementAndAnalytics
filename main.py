from datetime import datetime, timedelta

import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from pymongo import MongoClient
from starlette import status

# Initialize FastAPI app
app = FastAPI()

# MongoDB connection (replace with your MongoDB Atlas connection string)

# MONGO_URI = "mongodb+srv://TaskManagementAndAnalytics:<TaskManagementAndAnalyticsPassword>@terrin.szxvi1i.mongodb.net/?retryWrites=true&w=majority&appName=Terrin"
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client["task_db"]
users_collection = db["users"]
tasks_collection = db["tasks"]

# JWT settings
SECRET_KEY = "encode1234"  # Replace with a secure key in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Pydantic models
class User(BaseModel):
    username: str
    password: str




@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    user_dict = user.dict()
    user_dict["hashed_password"] = user_dict.pop("password")  # In production, hash the password
    users_collection.insert_one(user_dict)
    return {"message": "User registered successfully"}


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/login", response_model=Token)
async def login(user: User):
    db_user = users_collection.find_one({"username": user.username})
    if not db_user or db_user["hashed_password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


class Task(BaseModel):
    title: str
    description: str
    status: str  # e.g., "pending", "completed"
    due_date: str  # ISO format, e.g., "2025-10-30"
    assigned_to: str  # username

class TaskInDB(Task):
    id: str
    created_at: str

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = users_collection.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/tasks", response_model=TaskInDB)
async def create_task(task: Task, current_user: dict = Depends(get_current_user)):
    task_dict = task.dict()
    task_dict["created_at"] = datetime.utcnow().isoformat()
    task_dict["assigned_to"] = current_user["username"]
    result = tasks_collection.insert_one(task_dict)
    task_dict["id"] = str(result.inserted_id)
    return task_dict


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


