import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "mental_health_db")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]

# Collections
patients_collection = db["patients"]
doctors_collection = db["doctors"]
diagnosis_reports_collection = db["diagnosis_reports"]
doctor_patient_links_collection = db["doctor_patient_links"]
linkage_requests_collection = db["linkage_requests"]

# New collections for assessments and conversations
assessments_collection = db["assessments"]
assessment_results_collection = db["assessment_results"]
conversations_collection = db["conversations"]

# Create indices
async def setup_indices():
    await patients_collection.create_index("email", unique=True)
    await doctors_collection.create_index("email", unique=True)
    await patients_collection.create_index("id", unique=True)
    await doctors_collection.create_index("id", unique=True)
    await conversations_collection.create_index("patient_id")
    await assessment_results_collection.create_index("patient_id")
    await assessment_results_collection.create_index("assessment_id")
    await linkage_requests_collection.create_index([("doctor_id", 1), ("patient_id", 1)], unique=True) 