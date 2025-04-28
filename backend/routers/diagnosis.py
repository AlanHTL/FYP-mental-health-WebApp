from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Any, Optional
from models import (
    DiagnosisReport, 
    AssessmentResponse, 
    ScreeningRequest, 
    AssessmentRequest, 
    ReportRequest, 
    PatientInfo
)
from database import (
    diagnosis_reports_collection, 
    assessment_results_collection, 
    conversations_collection
)
from routers.auth import get_current_user
from datetime import datetime
from llm_agents import MentalHealthChatbot
from assessment_tools import get_assessment_list
import uuid

router = APIRouter()
chatbot = MentalHealthChatbot()

# Legacy endpoint for backward compatibility
@router.post("/chatbot", response_model=DiagnosisReport)
async def create_chatbot_diagnosis(
    symptoms: List[str],
    current_user: dict = Depends(get_current_user)
):
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create chatbot diagnoses"
        )
    
    try:
        # Process diagnosis through the LLM agents
        llm_results = await chatbot.process_diagnosis(symptoms)
        
        # Extract relevant information from the LLM results
        report_content = llm_results["report"]
        assessment = llm_results["assessment"]
        
        # Create diagnosis report
        diagnosis = {
            "id": str(datetime.utcnow().timestamp()),
            "patient_id": current_user["id"],
            "diagnosis": report_content.get("diagnosis", "Preliminary assessment based on symptoms"),
            "symptoms": symptoms,
            "recommendations": report_content.get("recommendations", [
                "Schedule a follow-up with a mental health professional",
                "Practice stress management techniques",
                "Maintain a regular sleep schedule",
                "Consider talking to a counselor or therapist"
            ]),
            "created_at": datetime.utcnow(),
            "is_physical": False,
            "llm_analysis": {
                "screening": llm_results["screening"],
                "assessment": assessment,
                "report": report_content
            }
        }
        
        await diagnosis_reports_collection.insert_one(diagnosis)
        return diagnosis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing diagnosis: {str(e)}"
        )

@router.get("/history", response_model=List[DiagnosisReport])
async def get_diagnosis_history(
    current_user: dict = Depends(get_current_user)
):
    """Get the diagnosis history for the current user."""
    if current_user["user_type"] not in ["patient", "doctor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view diagnosis history"
        )
    
    # If user is a patient, get their own history
    if current_user["user_type"] == "patient":
        patient_id = current_user["id"]
    # If user is a doctor, they must provide a patient_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor must use the /reports/{patient_id} endpoint"
        )
    
    reports = await diagnosis_reports_collection.find(
        {"patient_id": patient_id}
    ).sort("created_at", -1).to_list(length=None)
    
    return reports

@router.get("/reports/{patient_id}", response_model=List[DiagnosisReport])
async def get_patient_diagnosis_reports(
    patient_id: int,
    current_user: dict = Depends(get_current_user)
):
    # Check if user is authorized to view reports
    if current_user["user_type"] == "patient" and current_user["id"] != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these reports"
        )
    
    reports = await diagnosis_reports_collection.find(
        {"patient_id": patient_id}
    ).sort("created_at", -1).to_list(length=None)
    return reports

# New endpoints for the enhanced chatbot workflow

@router.get("/assessments")
async def get_available_assessments(
    current_user: dict = Depends(get_current_user)
):
    """Get a list of available standardized assessments."""
    from assessment_tools import get_assessment_list
    
    assessments = get_assessment_list()
    return assessments

@router.post("/screening/start")
async def start_screening_session(
    request: ScreeningRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a screening session with the chatbot.
    
    This is the first step of the assessment process where the patient
    provides initial symptoms and information for screening.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can start screening sessions"
        )
    
    # Create patient info from current user and request
    patient_info = {
        "name": f"{current_user['first_name']} {current_user['last_name']}",
        "age": request.patient_info.age,
        "gender": request.patient_info.gender or current_user.get("sex"),
        "chief_complaints": request.symptoms
    }
    
    # Start the screening session
    try:
        result = await chatbot.start_session(
            patient_info=patient_info,
            symptoms=request.symptoms
        )
        
        # Save session info to database
        session_data = {
            "id": result["session_id"],
            "patient_id": current_user["id"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "screening",
            "screening_result": result["screening_result"],
            "symptoms": request.symptoms,
            "patient_info": patient_info
        }
        
        await conversations_collection.insert_one(session_data)
        
        return {
            "session_id": result["session_id"],
            "message": result["screening_result"]["choices"][0]["message"]["content"],
            "recommended_assessments": result["screening_result"].get("recommended_assessments", ["DASS-21"])
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting screening: {str(e)}"
        )

@router.post("/assessment/start")
async def start_assessment(
    request: AssessmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start an assessment based on the recommended assessment from screening.
    
    This endpoint is called after screening is complete to start a specific
    standardized assessment (DASS-21 or PCL-5).
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can conduct assessments"
        )
    
    # Get session data
    session_data = await conversations_collection.find_one({"id": request.session_id})
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if the session belongs to the current user
    if session_data["patient_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Check if the screening is complete
    if session_data.get("status") not in ["screening_complete", "assessment"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Screening must be completed before starting assessment"
        )
    
    # Create patient info from database
    patient_info = session_data.get("patient_info", {})
    if not patient_info:
        patient_info = {
            "name": f"{current_user['first_name']} {current_user['last_name']}",
            "age": request.patient_info.age,
            "gender": request.patient_info.gender or current_user.get("sex")
        }
    
    try:
        # Start the assessment
        result = await chatbot.conduct_assessment(
            session_id=request.session_id,
            assessment_id=request.assessment_id,
            patient_info=patient_info
        )
        
        # Update session status in database
        await conversations_collection.update_one(
            {"id": request.session_id},
            {
                "$set": {
                    "status": "assessment",
                    "assessment_id": request.assessment_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Return assessment information
        return {
            "session_id": request.session_id,
            "assessment_id": request.assessment_id,
            "message": result["choices"][0]["message"]["content"],
            "questions": result["assessment_details"]["questions"],
            "options": result["assessment_details"]["options"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting assessment: {str(e)}"
        )

@router.post("/assessment/submit")
async def submit_assessment_responses(
    session_id: str = Body(...),
    assessment_id: str = Body(...),
    responses: List[int] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit responses to an assessment.
    
    This endpoint is called after the patient completes the assessment questions,
    to process their responses and calculate the assessment results.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can submit assessment responses"
        )
    
    # Get session data
    session_data = await conversations_collection.find_one({"id": session_id})
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if the session belongs to the current user
    if session_data["patient_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Ensure the correct assessment is being submitted
    if session_data.get("assessment_id") != assessment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected assessment {session_data.get('assessment_id')}, got {assessment_id}"
        )
    
    # Get patient info
    patient_info = session_data.get("patient_info", {})
    
    try:
        # Process the assessment responses
        result = await chatbot.process_assessment_responses(
            session_id=session_id,
            assessment_id=assessment_id,
            responses=responses,
            patient_info=patient_info
        )
        
        # Save the assessment results to the database
        assessment_result = {
            "id": str(uuid.uuid4()),
            "patient_id": current_user["id"],
            "session_id": session_id,
            "assessment_id": assessment_id,
            "responses": responses,
            "result": result,
            "created_at": datetime.utcnow()
        }
        
        await assessment_results_collection.insert_one(assessment_result)
        
        # Update session status
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$set": {
                    "status": "assessment_complete",
                    "assessment_result": result,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "assessment_id": assessment_id,
            "result": result,
            "interpretation": result.get("interpretation", {}).get("choices", [{}])[0].get("message", {}).get("content", "Assessment completed")
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing assessment responses: {str(e)}"
        )

@router.post("/report/generate")
async def generate_diagnosis_report(
    request: ReportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a comprehensive diagnostic report.
    
    This endpoint is called after the assessment is complete to generate a final
    report summarizing the screening, assessment results, and recommendations.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can generate reports"
        )
    
    # Get session data
    session_data = await conversations_collection.find_one({"id": request.session_id})
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if the session belongs to the current user
    if session_data["patient_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Check if assessment is complete
    if session_data.get("status") != "assessment_complete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment must be completed before generating a report"
        )
    
    # Update patient info with any new information
    patient_info = session_data.get("patient_info", {})
    patient_info.update({
        "name": f"{current_user['first_name']} {current_user['last_name']}",
        "patient_id": current_user["id"],
        "additional_info": request.additional_info
    })
    
    try:
        # Generate the report
        report = await chatbot.generate_report(
            session_id=request.session_id,
            patient_info=patient_info
        )
        
        # Save the report to the database
        diagnosis_report = {
            "id": str(uuid.uuid4()),
            "patient_id": current_user["id"],
            "session_id": request.session_id,
            "diagnosis": report.get("diagnosis", "Mental health assessment"),
            "symptoms": session_data.get("symptoms", []),
            "recommendations": report.get("recommendations", []),
            "created_at": datetime.utcnow(),
            "is_physical": False,
            "llm_analysis": {
                "screening": session_data.get("screening_result", {}),
                "assessment": session_data.get("assessment_result", {}),
                "report": report
            }
        }
        
        await diagnosis_reports_collection.insert_one(diagnosis_report)
        
        # Update session status
        await conversations_collection.update_one(
            {"id": request.session_id},
            {
                "$set": {
                    "status": "complete",
                    "report": report,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "report_id": diagnosis_report["id"],
            "diagnosis": report.get("diagnosis", "Mental health assessment"),
            "summary": report.get("summary", "Assessment completed"),
            "recommendations": report.get("recommendations", []),
            "full_report": report
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )

@router.post("/message")
async def send_message(
    session_id: str = Body(...),
    message: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to the chatbot in an ongoing conversation.
    
    This endpoint is used for back-and-forth communication with the chatbot
    throughout the screening, assessment, and report generation process.
    """
    try:
        # Verify the session exists and belongs to the user
        session_data = await conversations_collection.find_one({"id": session_id})
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session_data["patient_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # Process the message
        result = await chatbot.handle_message(session_id, message)
        
        # Update the conversation in the database
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "status": result.get("status", session_data.get("status", "screening"))
                }
            }
        )
        
        # Check if screening is complete and an assessment is recommended
        if result.get("status") == "screening_complete" and "diagnosis_json" in result:
            # Store the diagnosis JSON result
            await conversations_collection.update_one(
                {"id": session_id},
                {
                    "$set": {
                        "diagnosis_json": result["diagnosis_json"],
                        "recommended_assessment": result.get("recommended_assessment", "DASS-21")
                    }
                }
            )
            
            # Return the response with assessment information
            return {
                "message": result["message"],
                "diagnosis_json": result["diagnosis_json"],
                "recommended_assessment": result.get("recommended_assessment", "DASS-21")
            }
        
        # Return the standard message response
        return {"message": result["message"]}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        ) 