# Mental Health Diagnosis System setup menu
## WebApp functions:
Chatbot diagnosis function - RAG tool, Assessment, generate report

Report Viewer function

Patient-Doctor linkage function
## System Requirements
- **Python:** 3.9 or higher (recommended: 3.10+)
- **Node.js:** 16.x or higher (recommended: 18.x+)
- **npm:** 8.x or higher (comes with Node.js)
- **MongoDB:** 5.x or higher (local or remote instance)

---

## Project Structure
```
FYP-Group K/
  backend/
  frontend/
```
---
## Quick Setup of backend and frontend:
### 1. Environment Variables

Make sure that `.env` file is in the `backend/` directory. Example:

```
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=mental_health_db

# OpenAI API
API_KEY=your_openai_api_key
API_BASE=https://your-api-link/v1
```

- `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB`: Database name (default: `mental_health_db`)
- `API_KEY`: Your OpenAI API key (default: `sk-`)
- `API_BASE`: OpenAI API base URL (default: `https://xxxxxxxxx/v1`)

### 2. Auto start backend

Find the start_server.bat in .\backend
double click and run the start_server.bat

### 3. Auto start frontend
Find the start_frontend.bat in .\frontend double click and run the start_frontend.bat

## Backend Manual Setup

### 1. Environment Variables
make sure `.env` file is in the `backend/` directory.


### 2. Create python enviroment ,Install Python dependencies, and Start the Backend Server

2.1 Create python virtual enviroment & Activating the virtual environment in backend:
Open Terminal and navigate to the file first.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
```

2.2 install dependencies:

```bash
pip install -r requirements.txt
```

2.3 run the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Manual Setup

### 1. Install Node.js dependencies

Navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
```
### 2. Start the Frontend

```bash
npm start
```
---

## Troubleshooting

- Ensure MongoDB is running and accessible.
- Ensure your Python and Node.js versions meet the requirements.
- If you change `.env`, restart the backend.
- For OpenAI, ensure your API key is valid and has sufficient quota. 

---
## Started system and create user to test

### 1. register for new user of patients and doctors
### 2. login as patients to test the chatbot diagnosis function
### 3. Test others functions in the patient page and doctor page
