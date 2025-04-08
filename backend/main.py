from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, patients, doctors, diagnosis, linkage
from database import client

app = FastAPI(title="Mental Health Diagnosis System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(diagnosis.router, prefix="/api/diagnosis", tags=["Diagnosis"])
app.include_router(linkage.router, prefix="/api/linkage", tags=["Linkage"])

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

@app.get("/")
async def root():
    return {"message": "Welcome to Mental Health Diagnosis System API"} 