from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import LinkageRequest, Patient, Doctor
from database import linkage_requests_collection, patients_collection, doctors_collection
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.get("/my-requests", response_model=List[LinkageRequest])
async def get_my_linkage_requests(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can view their linkage requests"
        )
    
    requests = await linkage_requests_collection.find(
        {"patient_id": current_user["id"]}
    ).to_list(length=None)
    return requests

@router.get("/requests", response_model=List[LinkageRequest])
async def get_linkage_requests(current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can view linkage requests"
        )
    
    # Get all requests for the doctor
    requests = await linkage_requests_collection.find(
        {"doctor_id": current_user["id"]}
    ).to_list(length=None)
    
    # Create a list to store requests with patient info
    requests_with_patients = []
    
    # Fetch patient information for each request
    for request in requests:
        patient = await patients_collection.find_one({"id": request["patient_id"]})
        if patient:
            # Remove sensitive information
            patient.pop("password_hash", None)
            # Create a new request object with patient info
            request_with_patient = {
                "id": request["id"],
                "patient_id": request["patient_id"],
                "doctor_id": request["doctor_id"],
                "status": request["status"],
                "created_at": request["created_at"],
                "updated_at": request.get("updated_at", request["created_at"]),
                "patient": patient
            }
            requests_with_patients.append(request_with_patient)
    
    # Sort requests by created_at in descending order (newest first)
    requests_with_patients.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )
    
    return requests_with_patients

@router.post("/request/{doctor_id}", response_model=LinkageRequest)
async def create_linkage_request(
    doctor_id: int,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create linkage requests"
        )
    
    # Check if doctor exists
    doctor = await doctors_collection.find_one({"id": doctor_id})
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Check if request already exists
    existing_request = await linkage_requests_collection.find_one({
        "patient_id": current_user["id"],
        "doctor_id": doctor_id,
        "status": "pending"
    })
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linkage request already exists"
        )
    
    # Ensure ID values are integers
    patient_id = int(current_user["id"])
    doctor_id = int(doctor_id)
    
    # Create linkage request
    request = {
        "id": str(datetime.utcnow().timestamp()),
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    print(f"DEBUG: Creating linkage request - patient_id: {patient_id} (type: {type(patient_id)}), doctor_id: {doctor_id} (type: {type(doctor_id)})")
    
    await linkage_requests_collection.insert_one(request)
    return request

@router.put("/requests/{request_id}/approve", response_model=LinkageRequest)
async def approve_linkage_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can approve linkage requests"
        )
    
    request = await linkage_requests_collection.find_one({"id": request_id})
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linkage request not found"
        )
    
    if request["doctor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve this request"
        )
    
    # Ensure IDs are stored as integers
    patient_id = int(request["patient_id"])
    doctor_id = int(current_user["id"])
    
    print(f"DEBUG: Approving linkage request - patient_id: {patient_id} (type: {type(patient_id)}), doctor_id: {doctor_id} (type: {type(doctor_id)})")
    
    # Update request status
    await linkage_requests_collection.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Get updated request
    updated_request = await linkage_requests_collection.find_one({"id": request_id})
    if not updated_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Updated request not found"
        )
    
    # Get patient information
    patient = await patients_collection.find_one({"id": updated_request["patient_id"]})
    if patient:
        patient.pop("password_hash", None)
        return {
            "id": updated_request["id"],
            "patient_id": updated_request["patient_id"],
            "doctor_id": updated_request["doctor_id"],
            "status": updated_request["status"],
            "created_at": updated_request["created_at"],
            "updated_at": updated_request.get("updated_at", updated_request["created_at"]),
            "patient": patient
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Patient not found"
    )

@router.put("/requests/{request_id}/reject", response_model=LinkageRequest)
async def reject_linkage_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can reject linkage requests"
        )
    
    request = await linkage_requests_collection.find_one({"id": request_id})
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linkage request not found"
        )
    
    if request["doctor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reject this request"
        )
    
    # Update request status
    await linkage_requests_collection.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Get updated request
    updated_request = await linkage_requests_collection.find_one({"id": request_id})
    if not updated_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Updated request not found"
        )
    
    # Get patient information
    patient = await patients_collection.find_one({"id": updated_request["patient_id"]})
    if patient:
        patient.pop("password_hash", None)
        return {
            "id": updated_request["id"],
            "patient_id": updated_request["patient_id"],
            "doctor_id": updated_request["doctor_id"],
            "status": updated_request["status"],
            "created_at": updated_request["created_at"],
            "updated_at": updated_request.get("updated_at", updated_request["created_at"]),
            "patient": patient
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Patient not found"
    ) 