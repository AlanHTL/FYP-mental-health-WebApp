from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from models import Patient, DiagnosisReport
from database import patients_collection, diagnosis_reports_collection
from routers.auth import get_current_user
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class ChatbotDiagnosisRequest(BaseModel):
    diagnosis: str
    symptoms: List[str]
    recommendations: List[str]
    llm_analysis: Dict[str, Any]

@router.get("/me", response_model=Patient)
async def get_patient_info(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access patient information"
        )
    return current_user

@router.get("/reports", response_model=List[DiagnosisReport])
async def get_patient_reports(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access patient reports"
        )
    
    reports = await diagnosis_reports_collection.find(
        {"patient_id": current_user["id"]}
    ).to_list(length=None)
    return reports

