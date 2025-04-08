from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class Sex(str, Enum):
    MALE = "Male"
    FEMALE = "Female"

class UserBase(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    user_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PatientBase(UserBase):
    title: str
    sex: str
    date_of_birth: str
    phone_number: str

class Patient(PatientBase):
    pass

class Doctor(UserBase):
    title: str
    clinic_name: str
    clinic_location: str
    clinic_contact: str

class UserLogin(BaseModel):
    email: str
    password: str

class RegisterPatient(BaseModel):
    title: str
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    date_of_birth: str
    sex: str
    phone_number: str

class RegisterDoctor(BaseModel):
    title: str
    first_name: str
    last_name: str
    sex: str
    email: EmailStr
    password: str
    clinic_name: str
    clinic_location: str
    clinic_contact: str

class DiagnosisReport(BaseModel):
    id: str
    patient_id: int
    doctor_id: Optional[int] = None
    diagnosis: str
    symptoms: List[str]
    recommendations: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_physical: bool = False
    llm_analysis: Optional[Dict[str, Any]] = None

# New models for assessments

class AssessmentQuestion(BaseModel):
    text: str
    options: List[str]

class AssessmentResponse(BaseModel):
    assessment_id: str
    responses: List[int]
    
    @validator('responses')
    def validate_responses(cls, v, values):
        # Ensure responses are valid (0-3)
        if not all(0 <= response <= 3 for response in v):
            raise ValueError("All responses must be between 0 and 3")
        return v

class AssessmentResult(BaseModel):
    assessment_id: str
    patient_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responses: List[int]
    result: Dict[str, Any]
    
class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConversationHistory(BaseModel):
    id: str
    patient_id: int
    messages: List[ConversationMessage]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
class PatientInfo(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaints: List[str]
    
class ScreeningRequest(BaseModel):
    patient_info: PatientInfo
    symptoms: List[str]
    
class AssessmentRequest(BaseModel):
    patient_info: PatientInfo
    screening_result: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    
class ReportRequest(BaseModel):
    patient_info: PatientInfo
    screening_result: Dict[str, Any]
    assessment_result: Dict[str, Any]
    conversation_history: List[Dict[str, str]]

class LinkageRequest(BaseModel):
    id: str
    patient_id: int
    doctor_id: int
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    patient: Optional[Patient] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_type: Optional[str] = None  # "patient" or "doctor" 