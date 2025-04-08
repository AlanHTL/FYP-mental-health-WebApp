import asyncio
import httpx
import json

async def test_enhanced_chatbot_workflow():
    print("\n=== Starting Enhanced Chatbot Workflow Test ===")
    
    # Initialize client with longer timeout
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=httpx.Timeout(60.0)  # 60 seconds timeout
    ) as client:
        # Step 1: Register/Login
        print("\n1. Attempting registration...")
        registration_data = {
            "title": "Mr",
            "first_name": "Test",
            "last_name": "Patient",
            "email": "test@example.com",
            "password": "testpass123",
            "date_of_birth": "1990-01-01",
            "sex": "Male",
            "phone_number": "1234567890"
        }
        
        response = await client.post("/api/auth/register/patient", json=registration_data)
        print(f"Registration Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        # If already registered, try logging in
        if response.status_code == 400:
            print("\nUser already exists, attempting login...")
            login_data = {
                "email": "test@example.com",
                "password": "testpass123"
            }
            response = await client.post("/api/auth/login", json=login_data)
            print(f"Login Response: {response.status_code}")
            print(f"Response content: {response.text}")
        
        if response.status_code not in [200, 201]:
            raise Exception("Failed to authenticate")
        
        # Extract token
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Start Screening
        print("\n2. Starting screening session...")
        screening_data = {
            "patient_info": {
                "name": "Test Patient",
                "age": 30,
                "gender": "Male",
                "chief_complaints": [
                    "I've been feeling very anxious lately",
                    "Having trouble sleeping",
                    "Experiencing frequent headaches"
                ]
            },
            "symptoms": [
                "I've been feeling very anxious lately",
                "Having trouble sleeping",
                "Experiencing frequent headaches"
            ]
        }
        
        response = await client.post("/api/diagnosis/screening/start", json=screening_data, headers=headers)
        print(f"Screening Start Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to start screening: {response.text}")
        
        session_data = response.json()
        session_id = session_data.get("session_id")
        if not session_id:
            raise Exception(f"No session_id in response: {session_data}")
        
        # Step 3: Start Assessment
        print("\n3. Starting assessment...")
        start_assessment_data = {
            "session_id": session_id,
            "assessment_id": "GAD-7"  # Using GAD-7 as recommended by the screening
        }
        
        response = await client.post("/api/diagnosis/assessment/start", json=start_assessment_data, headers=headers)
        print(f"Assessment Start Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception("Failed to start assessment")
        
        # Step 4: Submit Assessment Responses
        print("\n4. Submitting assessment responses...")
        assessment_data = {
            "session_id": session_id,
            "assessment_id": "GAD-7",
            "responses": [2, 1, 2, 1, 2, 1, 2]  # Sample responses for GAD-7
        }
        
        response = await client.post("/api/diagnosis/assessment/submit", json=assessment_data, headers=headers)
        print(f"Assessment Submit Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception("Failed to submit assessment")
        
        # Step 5: Generate Report
        print("\n5. Generating diagnosis report...")
        response = await client.post(
            "/api/diagnosis/report/generate",
            content=session_id,
            headers={
                **headers,
                "Content-Type": "text/plain"
            }
        )
        print(f"Report Generation Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception("Failed to generate report")
        
        # Step 6: Verify Report in History
        print("\n6. Verifying report in history...")
        response = await client.get("/api/diagnosis/history", headers=headers)
        print(f"History Check Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception("Failed to retrieve history")

async def test_message_conversation():
    print("\n=== Starting Message Conversation Test ===")
    
    # Initialize client with longer timeout
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=httpx.Timeout(60.0)  # 60 seconds timeout
    ) as client:
        # Login
        print("\n1. Logging in...")
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        response = await client.post("/api/auth/login", json=login_data)
        print(f"Login Response: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception("Failed to login")
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Start screening session
        print("\n2. Starting conversation...")
        screening_data = {
            "patient_info": {
                "name": "Test Patient",
                "age": 30,
                "gender": "Male",
                "chief_complaints": ["I've been feeling anxious"]
            },
            "symptoms": ["I've been feeling anxious"]
        }
        
        response = await client.post("/api/diagnosis/screening/start", json=screening_data, headers=headers)
        print(f"Conversation Start Response: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            raise Exception("Failed to start conversation")
        
        session_data = response.json()
        session_id = session_data.get("session_id")
        if not session_id:
            raise Exception(f"No session_id in response: {session_data}")
        
        # Send messages
        messages = [
            "I've been feeling very anxious lately",
            "Yes, it's been affecting my sleep",
            "I also get headaches frequently"
        ]
        
        for msg in messages:
            print(f"\nSending message: {msg}")
            message_data = {
                "session_id": session_id,
                "message": msg
            }
            
            response = await client.post("/api/diagnosis/message", json=message_data, headers=headers)
            print(f"Message Response: {response.status_code}")
            print(f"Response content: {response.text}")
            
            if response.status_code != 200:
                raise Exception("Failed to send message")

async def main():
    try:
        await test_enhanced_chatbot_workflow()
        await test_message_conversation()
        print("\n=== All tests completed successfully ===")
    except Exception as e:
        print(f"\n!!! Test failed: {str(e)}")
        raise e

if __name__ == "__main__":
    asyncio.run(main()) 