# Mental Health Diagnosis System - API Documentation

This document provides comprehensive documentation for all API endpoints available in the Mental Health Diagnosis System.

## Base URL
All API endpoints are prefixed with: `http://localhost:8000`

## Authentication
Most endpoints require authentication using a Bearer token. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication

#### Register Patient
```http
POST /api/auth/register/patient
```
Request body:
```json
{
    "title": "string",
    "first_name": "string",
    "last_name": "string",
    "sex": "Male" | "Female",
    "email": "string",
    "date_of_birth": "YYYY-MM-DD",
    "phone_number": "string",
    "password": "string"
}
```
Response:
```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

#### Register Doctor
```http
POST /api/auth/register/doctor
```
Request body:
```json
{
    "title": "string",
    "first_name": "string",
    "last_name": "string",
    "sex": "Male" | "Female",
    "email": "string",
    "clinic_name": "string",
    "clinic_location": "string",
    "clinic_contact": "string",
    "password": "string"
}
```
Response:
```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

#### Login
```http
POST /api/auth/login
```
Request body (form data):
```
username: "email"
password: "password"
```
Response:
```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

### Patient Endpoints

#### Get Patient Profile
```http
GET /api/patients/me
```
Response:
```json
{
    "id": "integer",
    "title": "string",
    "first_name": "string",
    "last_name": "string",
    "sex": "Male" | "Female",
    "email": "string",
    "date_of_birth": "YYYY-MM-DD",
    "phone_number": "string",
    "created_at": "YYYY-MM-DDTHH:MM:SS"
}
```

### Doctor Endpoints

#### Get Doctor Profile
```http
GET /api/doctors/me
```
Response:
```json
{
    "id": "integer",
    "title": "string",
    "first_name": "string",
    "last_name": "string",
    "sex": "Male" | "Female",
    "email": "string",
    "clinic_name": "string",
    "clinic_location": "string",
    "clinic_contact": "string",
    "created_at": "YYYY-MM-DDTHH:MM:SS"
}
```

### Diagnosis Endpoints

#### Get Chatbot Diagnosis
```http
POST /api/diagnosis/chatbot
```
Request body:
```json
{
    "symptoms": ["string"]
}
```
Response:
```json
{
    "id": "string",
    "patient_id": "integer",
    "doctor_id": "integer | null",
    "diagnosis": "string",
    "symptoms": ["string"],
    "recommendations": ["string"],
    "created_at": "YYYY-MM-DDTHH:MM:SS",
    "is_physical": "boolean",
    "llm_analysis": {
        "screening": {
            "id": "string",
            "choices": [{
                "message": {
                    "content": "string"
                }
            }]
        },
        "assessment": {
            "id": "string",
            "choices": [{
                "message": {
                    "content": "string"
                }
            }]
        },
        "report": {
            "id": "string",
            "choices": [{
                "message": {
                    "content": "string"
                }
            }]
        }
    }
}
```

#### Get Diagnosis History
```http
GET /api/diagnosis/history
```
Response:
```json
[
    {
        "id": "string",
        "patient_id": "integer",
        "doctor_id": "integer | null",
        "diagnosis": "string",
        "symptoms": ["string"],
        "recommendations": ["string"],
        "created_at": "YYYY-MM-DDTHH:MM:SS",
        "is_physical": "boolean",
        "llm_analysis": {
            "screening": {
                "id": "string",
                "choices": [{
                    "message": {
                        "content": "string"
                    }
                }]
            },
            "assessment": {
                "id": "string",
                "choices": [{
                    "message": {
                        "content": "string"
                    }
                }]
            },
            "report": {
                "id": "string",
                "choices": [{
                    "message": {
                        "content": "string"
                    }
                }]
            }
        }
    }
]
```

### Linkage Endpoints

#### Request Doctor Linkage
```http
POST /api/linkage/request
```
Request body:
```json
{
    "doctor_id": "integer"
}
```
Response:
```json
{
    "id": "string",
    "patient_id": "integer",
    "doctor_id": "integer",
    "status": "pending" | "approved" | "rejected",
    "created_at": "YYYY-MM-DDTHH:MM:SS",
    "updated_at": "YYYY-MM-DDTHH:MM:SS"
}
```

#### Get Linkage Status
```http
GET /api/linkage/status
```
Response:
```json
{
    "id": "string",
    "patient_id": "integer",
    "doctor_id": "integer",
    "status": "pending" | "approved" | "rejected",
    "created_at": "YYYY-MM-DDTHH:MM:SS",
    "updated_at": "YYYY-MM-DDTHH:MM:SS"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "detail": "string"
}
```

### 401 Unauthorized
```json
{
    "detail": "Could not validate credentials",
    "headers": {
        "WWW-Authenticate": "Bearer"
    }
}
```

### 404 Not Found
```json
{
    "detail": "string"
}
```

### 500 Internal Server Error
```json
{
    "detail": "string"
}
```

## Example Usage

### Registering a Patient
```javascript
const response = await fetch('http://localhost:8000/api/auth/register/patient', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: "Mr",
        first_name: "John",
        last_name: "Doe",
        sex: "Male",
        email: "john.doe@example.com",
        date_of_birth: "1990-01-01",
        phone_number: "1234567890",
        password: "securepassword123"
    })
});
const data = await response.json();
```

### Getting Chatbot Diagnosis
```javascript
const response = await fetch('http://localhost:8000/api/diagnosis/chatbot', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
        symptoms: [
            "I've been feeling anxious lately",
            "Difficulty sleeping",
            "Loss of appetite"
        ]
    })
});
const data = await response.json();
```

## Notes

1. All dates are in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
2. The access token expires after 30 minutes
3. Passwords must be at least 8 characters long
4. Email addresses must be valid and unique
5. Phone numbers should be in a valid format
6. All string fields have appropriate length limits

# Backend LLM Agent & Diagnosis API

## Overview

This backend module provides the core logic for a mental health chatbot system, including:
- **`llm_agents.py`**: Implements the main logic for multi-agent mental health screening, assessment, and report generation using LLMs (Large Language Models) and retrieval-augmented generation (RAG).
- **`routers/diagnosis.py`**: Exposes FastAPI endpoints for chatbot-driven diagnosis, screening, assessment, and report generation, integrating with the LLM agent logic.

---

## llm_agents.py

### Purpose
- Orchestrates the chatbot's multi-step workflow: screening, assessment, and report generation.
- Uses OpenAI (or compatible) LLMs and a FAISS vector store for retrieval-augmented diagnosis.
- Handles conversation memory, session management, and fallback logic.

### Key Components
- **RAGScreeningAgent**: Uses retrieval-augmented generation to screen for mental health disorders based on user input and a vector database of disorder criteria.
- **AssessmentAgent**: (Placeholder) Handles standardized assessments (e.g., DASS-21, PCL-5). Can be extended for more complex logic.
- **ReportAgent**: (Placeholder) Generates summary reports based on screening and assessment results.
- **MentalHealthChatbot**: Main orchestrator class, manages sessions and delegates to the above agents.

### Development Notes
- The FAISS index is loaded from disk and used for semantic search of disorder criteria.
- The code is designed to be extensible for more advanced assessment/report logic.
- Fallbacks are provided if the LLM agent or vector store is unavailable.

---

## routers/diagnosis.py

### Purpose
- Exposes RESTful API endpoints for the chatbot workflow.
- Handles user authentication, session management, and database integration.
- Connects frontend requests to the LLM agent logic.

### Key Endpoints
- `POST /api/diagnosis/screening/start`: Start a new screening session with the chatbot.
- `POST /api/diagnosis/assessment/start`: Start a standardized assessment (e.g., DASS-21).
- `POST /api/diagnosis/assessment/submit`: Submit assessment responses and get results.
- `POST /api/diagnosis/report/generate`: Generate a comprehensive diagnostic report.
- `POST /api/diagnosis/message`: Send a message to the chatbot in an ongoing session.

### Development Notes
- Endpoints are designed to work with the current structure of `llm_agents.py`.
- Session and result data are stored in MongoDB collections.
- The API is secured with user authentication and role checks.
- The endpoints are compatible with both legacy and new chatbot workflows.

---

## Usage

1. **Start the FastAPI server** (from the `backend` directory):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Interact with the API** using the frontend or tools like Postman/curl.
3. **Extend the agents** in `llm_agents.py` for more advanced logic as needed.

---

## Extending/Customizing
- To add new assessments, update `assessment_tools.py` and extend `AssessmentAgent`.
- To improve report generation, implement more logic in `ReportAgent`.
- To change the retrieval database, update the FAISS index and vector store logic.

---

## Contact
For questions or contributions, please contact the project maintainer. 