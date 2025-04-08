from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import Patient, DiagnosisReport
from database import patients_collection, diagnosis_reports_collection
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

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

@router.post("/chatbot-diagnosis", response_model=DiagnosisReport)
async def create_chatbot_diagnosis(
    symptoms: List[str],
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create diagnosis reports"
        )
    
    # TODO: Implement LLM chatbot diagnosis logic here
    # For now, we'll create a dummy diagnosis
    diagnosis = {
        "id": str(datetime.utcnow().timestamp()),
        "patient_id": current_user["id"],
        "diagnosis": "Preliminary assessment based on symptoms",
        "symptoms": symptoms,
        "recommendations": [
            "Schedule a follow-up with a mental health professional",
            "Practice stress management techniques",
            "Maintain a regular sleep schedule"
        ],
        "created_at": datetime.utcnow(),
        "is_physical": False
    }
    
    await diagnosis_reports_collection.insert_one(diagnosis)
    return diagnosis 