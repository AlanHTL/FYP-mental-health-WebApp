from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import Doctor, DiagnosisReport, Patient
from database import doctors_collection, diagnosis_reports_collection, patients_collection, linkage_requests_collection
from routers.auth import get_current_user
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# Create a request model for diagnosis creation
class DiagnosisRequest(BaseModel):
    patient_id: int
    diagnosis: str
    details: str
    symptoms: List[str]
    recommendations: List[str]

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
    
    # Ensure doctor_id is an integer
    doctor_id = int(current_user["id"])
    
    print(f"DEBUG: Fetching linked patients for doctor ID: {doctor_id} (type: {type(doctor_id)})")
    
    # Find all approved linkage requests for this doctor
    approved_requests = await linkage_requests_collection.find(
        {"doctor_id": doctor_id, "status": "approved"}
    ).to_list(length=None)
    
    print(f"DEBUG: Found {len(approved_requests)} approved linkage requests")
    
    # Get patient IDs from these requests and ensure they are integers
    patient_ids = [int(request["patient_id"]) for request in approved_requests]
    
    print(f"DEBUG: Patient IDs: {patient_ids}")
    
    # If no linked patients, return empty list
    if not patient_ids:
        print("DEBUG: No linked patients found")
        return []
    
    # Find all patients with matching IDs
    linked_patients = await patients_collection.find(
        {"id": {"$in": patient_ids}}
    ).to_list(length=None)
    
    print(f"DEBUG: Found {len(linked_patients)} linked patient records")
    
    # Remove sensitive information
    for patient in linked_patients:
        patient.pop("password_hash", None)
    
    return linked_patients

@router.post("/physical-diagnosis", response_model=DiagnosisReport)
async def create_physical_diagnosis(
    request: DiagnosisRequest,
    current_user: dict = Depends(get_current_user)
):
    print(f"DEBUG: Creating physical diagnosis for patient ID: {request.patient_id}")
    print(f"DEBUG: Doctor ID: {current_user['id']}")
    print(f"DEBUG: Diagnosis: {request.diagnosis}")
    print(f"DEBUG: Details: {request.details}")
    print(f"DEBUG: Symptoms: {request.symptoms}")
    print(f"DEBUG: Recommendations: {request.recommendations}")
    
    if current_user["user_type"] != "doctor":
        print(f"ERROR: Unauthorized user type: {current_user['user_type']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create physical diagnosis reports"
        )
    
    # Check if patient exists
    patient = await patients_collection.find_one({"id": request.patient_id})
    if not patient:
        print(f"ERROR: Patient with ID {request.patient_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    print(f"DEBUG: Patient found: {patient['first_name']} {patient['last_name']}")
    
    # Create diagnosis report
    diagnosis_report = {
        "id": str(datetime.utcnow().timestamp()),
        "patient_id": request.patient_id,
        "doctor_id": current_user["id"],
        "diagnosis": request.diagnosis,
        "details": request.details,
        "symptoms": request.symptoms,
        "recommendations": request.recommendations,
        "created_at": datetime.utcnow(),
        "is_physical": True  # Always true for doctor-created reports
    }
    
    try:
        await diagnosis_reports_collection.insert_one(diagnosis_report)
        print(f"DEBUG: Diagnosis report created successfully with ID: {diagnosis_report['id']}")
    except Exception as e:
        print(f"ERROR: Failed to create diagnosis report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create diagnosis report: {str(e)}"
        )
    
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
    
    # Ensure patient_id is an integer
    patient_id = int(patient_id)
    
    print(f"DEBUG: Fetching reports for patient ID: {patient_id} (type: {type(patient_id)})")
    
    # Check if doctor is linked with the patient
    linkage = await linkage_requests_collection.find_one({
        "doctor_id": int(current_user["id"]),
        "patient_id": patient_id,
        "status": "approved"
    })
    
    if not linkage:
        print(f"DEBUG: No linkage found between doctor {current_user['id']} and patient {patient_id}")
        # For now, we'll still return reports even without linkage, but log the issue
    else:
        print(f"DEBUG: Found linkage between doctor {current_user['id']} and patient {patient_id}")
    
    reports = await diagnosis_reports_collection.find(
        {"patient_id": patient_id}
    ).to_list(length=None)
    
    print(f"DEBUG: Found {len(reports)} reports for patient {patient_id}")
    
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