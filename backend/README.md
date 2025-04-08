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