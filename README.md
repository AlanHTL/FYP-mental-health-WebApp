# Mental Health Diagnosis Multi-Agent System

A comprehensive mental health diagnosis system using multiple AI agents for screening, assessment, and report generation.

## Overview

The Mental Health Diagnosis system consists of three main components:

1. **Screening Agent**: Uses RAG (Retrieval Augmented Generation) with a FAISS vector database to analyze patient symptoms and provide an initial diagnosis.

2. **Assessment Agent**: Conducts standardized assessments based on the screening results:
   - DASS-21 for depression, anxiety, and stress disorders
   - PCL-5 for PTSD (Posttraumatic Stress Disorder)

3. **Report Generator Agent**: Creates a comprehensive report based on the screening and assessment results.

## System Architecture

### Backend

The backend is built using FastAPI and includes:

- **llm_agents.py**: Contains the multi-agent system implementation
- **assessment_tools.py**: Contains assessment tools (DASS-21, PCL-5, etc.)
- **routers/diagnosis.py**: API endpoints for the diagnosis workflow
- **faiss_index/**: Vector database for mental health disorder information

### Frontend

The frontend is built with React and Material-UI:

- **ChatbotDiagnosis.tsx**: Main component that guides users through the diagnosis process
- Includes a step-by-step workflow:
  1. Screening conversation
  2. Assessment selection
  3. Assessment questions
  4. Report generation
  5. Final report view

## Setup and Installation

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Set environment variables:
   ```
   API_KEY=sk-UnNXXoNG6qqa1RUl24zKrakQaHBeyxqkxEtaVwGbSrGlRQxl
   API_BASE=https://xiaoai.plus/v1
   ```

6. Start the backend server:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

## Usage

1. **Screening**: Start by describing your symptoms to the chatbot. The system will use RAG to find relevant mental health information and provide an initial diagnosis.

2. **Assessment**: Based on the screening results, the system will recommend an appropriate assessment:
   - DASS-21 for depression, anxiety, and stress-related symptoms
   - PCL-5 for PTSD symptoms

3. **Report Generation**: After completing the assessment, you can generate a comprehensive report that includes diagnosis, severity, and recommendations.

## Technical Details

- The system uses OpenAI's GPT models for natural language processing
- RAG (Retrieval Augmented Generation) with FAISS vector database improves diagnosis accuracy by incorporating specific mental health disorder criteria
- Assessment tools follow standardized scoring methods for reliable results

## License

This project is proprietary and for demonstration purposes only. 