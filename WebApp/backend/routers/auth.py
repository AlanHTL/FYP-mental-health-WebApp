from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from models import UserLogin, Token, TokenData, RegisterPatient, RegisterDoctor
from database import patients_collection, doctors_collection
import random
import os
import secrets

router = APIRouter()

# Security
SECRET_KEY = os.getenv("SECRET_KEY")  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ID Generation settings
MIN_ID = 10000  # Start from 10000 to have more digits
MAX_ID = 99999  # 5 digits
MAX_ATTEMPTS = 10  # Maximum attempts to generate a unique ID

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_type=user_type)
    except JWTError:
        raise credentials_exception
    
    # Try to find user in appropriate collection based on user_type
    if token_data.user_type == "patient":
        user = await patients_collection.find_one({"email": token_data.email})
    else:
        user = await doctors_collection.find_one({"email": token_data.email})
    
    if user is None:
        raise credentials_exception
    return user

async def generate_unique_id() -> int:
    """Generate a unique ID with collision checking"""
    for _ in range(MAX_ATTEMPTS):
        # Use secrets for cryptographically secure random number
        new_id = secrets.randbelow(MAX_ID - MIN_ID + 1) + MIN_ID
        
        # Check if ID exists in either collection
        existing_patient = await patients_collection.find_one({"id": new_id})
        existing_doctor = await doctors_collection.find_one({"id": new_id})
        
        if not existing_patient and not existing_doctor:
            return new_id
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate unique ID after maximum attempts"
    )

@router.post("/register/patient", response_model=Token)
async def register_patient(patient: RegisterPatient):
    # Check if email already exists
    if await patients_collection.find_one({"email": patient.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate a unique ID
    patient_id = await generate_unique_id()
    
    # Hash the password
    hashed_password = pwd_context.hash(patient.password)
    
    # Create patient document
    patient_dict = patient.dict()
    patient_dict["password"] = hashed_password
    patient_dict["user_type"] = "patient"
    patient_dict["id"] = patient_id
    patient_dict["created_at"] = datetime.utcnow()
    
    # Insert into database
    await patients_collection.insert_one(patient_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": patient.email, "user_type": "patient"}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register/doctor", response_model=Token)
async def register_doctor(doctor: RegisterDoctor):
    # Check if email already exists
    if await doctors_collection.find_one({"email": doctor.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate a unique ID
    doctor_id = await generate_unique_id()
    
    # Hash the password
    hashed_password = pwd_context.hash(doctor.password)
    
    # Create doctor document
    doctor_dict = doctor.dict()
    doctor_dict["password"] = hashed_password
    doctor_dict["user_type"] = "doctor"
    doctor_dict["id"] = doctor_id
    doctor_dict["created_at"] = datetime.utcnow()
    
    # Insert into database
    await doctors_collection.insert_one(doctor_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": doctor.email, "user_type": "doctor"}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: UserLogin):
    # Try to find user in patients collection
    user = await patients_collection.find_one({"email": form_data.email})
    user_type = "patient"
    
    # If not found in patients, try doctors collection
    if not user:
        user = await doctors_collection.find_one({"email": form_data.email})
        user_type = "doctor"
    
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": form_data.email, "user_type": user_type}
    )
    return {"access_token": access_token, "token_type": "bearer"} 