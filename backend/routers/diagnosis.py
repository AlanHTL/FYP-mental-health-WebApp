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
    session_id: str = Body(...),
    assessment_id: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Start the assessment phase after screening.
    
    This is the second step where the appropriate assessment is selected
    based on the screening results.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can conduct assessments"
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
    
    try:
        # Conduct the assessment
        assessment_result = await chatbot.conduct_assessment(
            session_id=session_id,
            assessment_id=assessment_id,
            patient_info=session_data["patient_info"],
            screening_result=session_data["screening_result"]
        )
        
        # Update session status
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$set": {
                    "status": "assessment",
                    "assessment_id": assessment_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "session_id": session_id,
            "assessment_id": assessment_id,
            "message": assessment_result["choices"][0]["message"]["content"],
            "questions": assessment_result["assessment_details"]["questions"],
            "options": assessment_result["assessment_details"]["options"]
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
    Submit responses to an assessment and get the results.
    
    This completes the assessment phase and prepares for the report generation.
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
    
    try:
        # Process assessment responses
        assessment_results = await chatbot.process_assessment_responses(
            session_id=session_id,
            assessment_id=assessment_id,
            responses=responses,
            patient_info=session_data["patient_info"]
        )
        
        # Save assessment results to database
        result_data = {
            "id": f"{session_id}_{assessment_id}",
            "session_id": session_id,
            "patient_id": current_user["id"],
            "assessment_id": assessment_id,
            "responses": responses,
            "results": assessment_results["numerical_results"],
            "created_at": datetime.utcnow()
        }
        
        await assessment_results_collection.insert_one(result_data)
        
        # Update session data
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$set": {
                    "status": "results",
                    "assessment_results": assessment_results,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "session_id": session_id,
            "assessment_id": assessment_id,
            "results": assessment_results["numerical_results"],
            "interpretation": assessment_results["interpretation"]["choices"][0]["message"]["content"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing assessment responses: {str(e)}"
        )

@router.post("/report/generate")
async def generate_diagnosis_report(
    session_id: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate the final diagnosis report.
    
    This is the third and final step where all collected information is
    synthesized into a comprehensive diagnosis report.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can generate diagnosis reports"
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
    
    # Check if assessment results are available
    if "assessment_results" not in session_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment results not found for this session"
        )
    
    try:
        # Generate report
        report = await chatbot.generate_report(
            session_id=session_id,
            patient_info=session_data["patient_info"],
            symptoms=session_data["symptoms"],
            screening_result=session_data["screening_result"],
            assessment_results=session_data["assessment_results"]
        )
        
        # Create diagnosis report
        diagnosis = {
            "id": str(datetime.utcnow().timestamp()),
            "patient_id": current_user["id"],
            "diagnosis": report.get("diagnosis", "Preliminary assessment based on symptoms"),
            "symptoms": session_data["symptoms"],
            "recommendations": report.get("recommendations", [
                "Schedule a follow-up with a mental health professional",
                "Practice stress management techniques",
                "Maintain a regular sleep schedule"
            ]),
            "created_at": datetime.utcnow(),
            "is_physical": False,
            "llm_analysis": {
                "screening": session_data["screening_result"],
                "assessment": session_data["assessment_results"],
                "report": report
            }
        }
        
        # Save diagnosis report to database
        await diagnosis_reports_collection.insert_one(diagnosis)
        
        # Update session status
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$set": {
                    "status": "completed",
                    "report": report,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "session_id": session_id,
            "diagnosis": report.get("diagnosis"),
            "report": report["choices"][0]["message"]["content"],
            "recommendations": report.get("recommendations", []),
            "report_id": diagnosis["id"]
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
    Send a message to the chatbot in an ongoing session.
    
    This allows for interactive conversation during any phase of the assessment.
    """
    if current_user["user_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can send messages to the chatbot"
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
    
    try:
        # Send message to chatbot
        response = await chatbot.handle_message(
            session_id=session_id,
            message=message
        )
        
        # Update session data
        await conversations_collection.update_one(
            {"id": session_id},
            {
                "$push": {
                    "messages": {
                        "role": "user",
                        "content": message,
                        "timestamp": datetime.utcnow()
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Add chatbot response to session data
        if response.get('choices') and len(response['choices']) > 0:
            await conversations_collection.update_one(
                {"id": session_id},
                {
                    "$push": {
                        "messages": {
                            "role": "assistant",
                            "content": response['choices'][0]['message']['content'],
                            "timestamp": datetime.utcnow()
                        }
                    }
                }
            )
        
        return {
            "session_id": session_id,
            "message": response['choices'][0]['message']['content']
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        ) 