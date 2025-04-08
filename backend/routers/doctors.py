from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import Doctor, DiagnosisReport, Patient
from database import doctors_collection, diagnosis_reports_collection, patients_collection, linkage_requests_collection
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=List[Doctor])
async def get_all_doctors(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can view the list of doctors"
        )
    
    doctors = await doctors_collection.find().to_list(length=None)
    return doctors

@router.get("/me", response_model=Doctor)
async def get_doctor_info(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access doctor information"
        )
    return current_user

@router.get("/linked-patients", response_model=List[Patient])
async def get_linked_patients(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access linked patients"
        )
    
    # Find all approved linkage requests for this doctor
    approved_requests = await linkage_requests_collection.find(
        {"doctor_id": current_user["id"], "status": "approved"}
    ).to_list(length=None)
    
    # Get patient IDs from these requests
    patient_ids = [request["patient_id"] for request in approved_requests]
    
    # If no linked patients, return empty list
    if not patient_ids:
        return []
    
    # Find all patients with matching IDs
    linked_patients = await patients_collection.find(
        {"id": {"$in": patient_ids}}
    ).to_list(length=None)
    
    # Remove sensitive information
    for patient in linked_patients:
        patient.pop("password_hash", None)
    
    return linked_patients

@router.post("/physical-diagnosis", response_model=DiagnosisReport)
async def create_physical_diagnosis(
    patient_id: int,
    diagnosis: str,
    symptoms: List[str],
    recommendations: List[str],
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create physical diagnosis reports"
        )
    
    # Check if patient exists
    patient = await patients_collection.find_one({"id": patient_id})
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Create diagnosis report
    diagnosis_report = {
        "id": str(datetime.utcnow().timestamp()),
        "patient_id": patient_id,
        "doctor_id": current_user["id"],
        "diagnosis": diagnosis,
        "symptoms": symptoms,
        "recommendations": recommendations,
        "created_at": datetime.utcnow(),
        "is_physical": True
    }
    
    await diagnosis_reports_collection.insert_one(diagnosis_report)
    return diagnosis_report

@router.get("/patient-reports/{patient_id}", response_model=List[DiagnosisReport])
async def get_patient_reports(
    patient_id: int,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access patient reports"
        )
    
    # TODO: Check if doctor is linked with the patient
    reports = await diagnosis_reports_collection.find(
        {"patient_id": patient_id}
    ).to_list(length=None)
    return reports

@router.get("/{doctor_id}", response_model=Doctor)
async def get_doctor_by_id(
    doctor_id: int,
    current_user: dict = Depends(get_current_user)
):
    # Check if doctor exists
    doctor = await doctors_collection.find_one({"id": doctor_id})
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Remove sensitive information
    doctor.pop("password_hash", None)
    
    return doctor 