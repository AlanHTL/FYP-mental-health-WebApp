from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta
from collections import deque
import json
from openai import AsyncOpenAI
from fastapi import HTTPException, status
from assessment_tools import get_assessment, get_assessment_list, calculate_assessment_result
import uuid

load_dotenv()

API_KEY = os.getenv("API_KEY")
RATE_LIMIT_REQUESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 10  # seconds

if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

# Initialize OpenAI client with custom base URL
client = AsyncOpenAI(
    base_url="https://xiaoai.plus/v1",
    api_key=API_KEY
)

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    async def acquire(self):
        now = datetime.now()
        # Remove old requests
        while self.requests and (now - self.requests[0]) > timedelta(seconds=self.window_seconds):
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            # Wait until the oldest request expires
            wait_time = (self.requests[0] + timedelta(seconds=self.window_seconds) - now).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)

rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)

class BaseAgent:
    async def _make_api_call(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        await rate_limiter.acquire()
        try:
            async with asyncio.timeout(30):  # 30-second timeout
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7
                )
                return response.model_dump()
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="LLM API request timed out"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API call failed: {str(e)}"
            )

class ScreeningAgent(BaseAgent):
    async def screen_patient(self, patient_info: Dict[str, Any], symptoms: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Initial screening to gather patient information and identify potential mental health issues.
        
        Args:
            patient_info: Basic information about the patient
            symptoms: List of symptoms reported by the patient
            conversation_history: Previous conversation history, if any
            
        Returns:
            Screening results including potential issues and recommended assessments
        """
        messages = [
            {"role": "system", "content": """You are a mental health screening agent. Your job is to:
1. Ask appropriate questions to understand the patient's situation
2. Determine potential mental health issues based on reported symptoms
3. Recommend appropriate standardized assessments (DASS-21, GAD-7, PHQ-9) based on the information
4. Never suggest self-harm or harmful behaviors
5. Maintain a professional, compassionate tone"""},
            {"role": "user", "content": f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Reported symptoms: {', '.join(symptoms)}

Based on this information, please:
1. Ask 3-5 appropriate follow-up questions to better understand their situation
2. Provide a preliminary assessment of potential mental health issues
3. Recommend which standardized assessment(s) would be most appropriate (DASS-21, GAD-7, or PHQ-9)
4. Explain why you recommend these assessments
"""}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            # Insert conversation history before the last message
            for message in conversation_history:
                messages.insert(-1, message)
        
        response = await self._make_api_call(messages)
        
        # Extract recommended assessments using another API call
        assessment_extraction_messages = [
            {"role": "system", "content": "You are an AI assistant that extracts information from text."},
            {"role": "user", "content": f"""Based on the following screening result, list ONLY the recommended assessment IDs (DASS-21, GAD-7, or PHQ-9) that should be administered.
            
Screening result:
{response.get('choices', [{}])[0].get('message', {}).get('content', '')}

Return your answer as a JSON array with ONLY the assessment IDs, like this: ["DASS-21", "GAD-7"]
"""}
        ]
        
        assessment_response = await self._make_api_call(assessment_extraction_messages)
        assessment_content = assessment_response.get('choices', [{}])[0].get('message', {}).get('content', '[]')
        
        # Try to extract the JSON list
        try:
            # Find JSON array in the text
            import re
            json_match = re.search(r'\[(.*?)\]', assessment_content)
            if json_match:
                assessment_content = f"[{json_match.group(1)}]"
            
            recommended_assessments = json.loads(assessment_content)
            if not isinstance(recommended_assessments, list):
                recommended_assessments = ["DASS-21"]  # Default to DASS-21 if parsing fails
        except json.JSONDecodeError:
            recommended_assessments = ["DASS-21"]  # Default to DASS-21 if parsing fails
        
        # Add the recommended assessments to the response
        response["recommended_assessments"] = recommended_assessments
        return response

class AssessmentAgent(BaseAgent):
    async def conduct_assessment(self, assessment_id: str, patient_info: Dict[str, Any], screening_result: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Conduct a standardized assessment based on the screening results.
        
        Args:
            assessment_id: The ID of the assessment to conduct (e.g., "DASS-21")
            patient_info: Basic information about the patient
            screening_result: Results from the screening phase
            conversation_history: Previous conversation history
            
        Returns:
            Assessment instructions and questions
        """
        try:
            assessment = get_assessment(assessment_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assessment {assessment_id} not found"
            )
        
        questions = assessment["questions"]
        options = assessment["options"]
        description = assessment["description"]
        
        messages = [
            {"role": "system", "content": f"""You are a mental health assessment agent specialized in administering the {assessment_id} assessment. 
Your job is to:
1. Explain the assessment process to the patient
2. Present each question professionally and clearly
3. Collect their responses accurately
4. Be supportive and non-judgmental throughout
5. Never suggest self-harm or harmful behaviors

About this assessment: {description}

The assessment has {len(questions)} questions with the following response options:
{', '.join(f'{i}. {option}' for i, option in enumerate(options))}"""},
            {"role": "user", "content": f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Screening result summary:
{screening_result.get('choices', [{}])[0].get('message', {}).get('content', 'No screening data available')}

Please:
1. Introduce the {assessment_id} assessment to the patient
2. Explain how it works (rating scale, purpose, etc.)
3. Emphasize the importance of honest answers
4. Let them know this is just one part of a comprehensive evaluation
"""}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            # Insert conversation history before the last message
            for message in conversation_history:
                messages.insert(-1, message)
        
        response = await self._make_api_call(messages)
        
        # Add assessment details to the response
        response["assessment_details"] = {
            "id": assessment_id,
            "name": assessment["name"],
            "description": description,
            "questions": questions,
            "options": options
        }
        
        return response
    
    async def process_assessment_results(self, assessment_id: str, responses: List[int], patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the results of an assessment.
        
        Args:
            assessment_id: The ID of the assessment
            responses: List of numerical responses to the assessment questions
            patient_info: Basic information about the patient
            
        Returns:
            Processed assessment results and interpretation
        """
        try:
            # Calculate the assessment result
            result = calculate_assessment_result(assessment_id, responses)
            
            # Get more detailed interpretation via LLM
            assessment = get_assessment(assessment_id)
            questions = assessment["questions"]
            options = assessment["options"]
            
            # Create a summary of the responses
            response_summary = []
            for i, (question, response) in enumerate(zip(questions, responses)):
                response_summary.append(f"Q{i+1}: '{question}' - Response: '{options[response]}' ({response}/3)")
            
            messages = [
                {"role": "system", "content": f"""You are a mental health assessment expert specializing in the {assessment_id} assessment.
Your job is to:
1. Interpret assessment results accurately and professionally
2. Explain what the scores mean in plain language
3. Provide appropriate recommendations based on the results
4. Be mindful of the sensitivity of mental health issues
5. Never suggest self-harm or harmful behaviors"""},
                {"role": "user", "content": f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

{assessment_id} Assessment Results:
{json.dumps(result, indent=2)}

Patient Responses:
{chr(10).join(response_summary)}

Please:
1. Interpret these results in a clear, compassionate way
2. Explain what these scores indicate about the patient's mental health
3. Suggest appropriate next steps based on these results
4. Mention any limitations of this assessment
"""}
            ]
            
            interpretation = await self._make_api_call(messages)
            
            # Combine the calculated result with the interpretation
            return {
                "assessment_id": assessment_id,
                "numerical_results": result,
                "interpretation": interpretation
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing assessment results: {str(e)}"
            )

class ReportAgent(BaseAgent):
    async def generate_report(
        self,
        patient_info: Dict[str, Any],
        symptoms: List[str],
        screening_result: Dict[str, Any],
        assessment_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive diagnosis report based on all collected information.
        
        Args:
            patient_info: Basic information about the patient
            symptoms: List of symptoms reported by the patient
            screening_result: Results from the screening phase
            assessment_results: Results from the assessment phase
            conversation_history: Full conversation history
            
        Returns:
            Comprehensive diagnosis report
        """
        screening_content = screening_result.get('choices', [{}])[0].get('message', {}).get('content', 'No screening data available')
        
        # Extract assessment interpretation
        assessment_interpretation = assessment_results.get('interpretation', {})
        assessment_interpretation_content = assessment_interpretation.get('choices', [{}])[0].get('message', {}).get('content', 'No assessment interpretation available')
        
        # Extract numerical results
        numerical_results = assessment_results.get('numerical_results', {})
        assessment_id = assessment_results.get('assessment_id', 'Unknown assessment')
        
        messages = [
            {"role": "system", "content": """You are a mental health report generation agent. Your job is to:
1. Synthesize all patient information into a clear, comprehensive report
2. Provide an accurate diagnostic impression based on symptoms and assessment results
3. Suggest appropriate treatment recommendations
4. Maintain a professional, clinical tone
5. Never suggest self-harm or harmful behaviors
6. Be thorough but concise"""},
            {"role": "user", "content": f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Reported Symptoms:
{', '.join(symptoms)}

Screening Results:
{screening_content}

Assessment Used: {assessment_id}
Numerical Results:
{json.dumps(numerical_results, indent=2)}

Assessment Interpretation:
{assessment_interpretation_content}

Please generate a comprehensive mental health report including:
1. Executive summary
2. Detailed clinical findings
3. Diagnostic impression (based on reported symptoms and assessment results)
4. Treatment recommendations
5. Follow-up suggestions

Format the report in a professional clinical style.
"""}
        ]
        
        # We don't need to include the entire conversation history here
        # as we already have the summary and interpretations
        
        report_response = await self._make_api_call(messages)
        
        # Extract recommendations using another API call
        recommendations_extraction_messages = [
            {"role": "system", "content": "You are an AI assistant that extracts information from text."},
            {"role": "user", "content": f"""Based on the following report, extract the key treatment recommendations and follow-up suggestions.
            
Report:
{report_response.get('choices', [{}])[0].get('message', {}).get('content', '')}

Return your answer as a JSON array of recommendation strings.
"""}
        ]
        
        recommendations_response = await self._make_api_call(recommendations_extraction_messages)
        recommendations_content = recommendations_response.get('choices', [{}])[0].get('message', {}).get('content', '[]')
        
        # Try to extract the recommendations as a JSON list
        try:
            # Find JSON array in the text
            import re
            json_match = re.search(r'\[(.*?)\]', recommendations_content)
            if json_match:
                recommendations_content = f"[{json_match.group(1)}]"
            
            recommendations = json.loads(recommendations_content)
            if not isinstance(recommendations, list):
                recommendations = ["Schedule a follow-up with a mental health professional"]
        except json.JSONDecodeError:
            recommendations = ["Schedule a follow-up with a mental health professional"]
        
        # Extract diagnosis using another API call
        diagnosis_extraction_messages = [
            {"role": "system", "content": "You are an AI assistant that extracts information from text."},
            {"role": "user", "content": f"""Based on the following report, extract the primary diagnosis or diagnostic impression.
            
Report:
{report_response.get('choices', [{}])[0].get('message', {}).get('content', '')}

Return only the primary diagnosis as a single string.
"""}
        ]
        
        diagnosis_response = await self._make_api_call(diagnosis_extraction_messages)
        diagnosis = diagnosis_response.get('choices', [{}])[0].get('message', {}).get('content', 'Preliminary assessment based on symptoms')
        
        # Add the extracted information to the response
        report_response["recommendations"] = recommendations
        report_response["diagnosis"] = diagnosis
        report_response["assessment_results"] = numerical_results
        
        return report_response

class MentalHealthChatbot:
    def __init__(self):
        self.screening_agent = ScreeningAgent()
        self.assessment_agent = AssessmentAgent()
        self.report_agent = ReportAgent()
        self.conversation_history = {}  # Store conversation history by session ID

    async def start_session(self, patient_info: Dict[str, Any], symptoms: List[str]) -> Dict[str, Any]:
        """
        Start a new chatbot session with screening.
        
        Args:
            patient_info: Basic information about the patient
            symptoms: Initial symptoms reported by the patient
            
        Returns:
            Session ID and screening results
        """
        session_id = str(uuid.uuid4())
        
        # Initialize conversation history
        self.conversation_history[session_id] = []
        
        # Perform initial screening
        screening_result = await self.screening_agent.screen_patient(
            patient_info=patient_info,
            symptoms=symptoms
        )
        
        # Update conversation history
        if screening_result.get('choices') and len(screening_result['choices']) > 0:
            self.conversation_history[session_id].append(
                {"role": "assistant", "content": screening_result['choices'][0]['message']['content']}
            )
        
        return {
            "session_id": session_id,
            "screening_result": screening_result
        }
    
    async def conduct_assessment(self, session_id: str, assessment_id: str, patient_info: Dict[str, Any], screening_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct an assessment based on screening results.
        
        Args:
            session_id: Session ID from the screening phase
            assessment_id: ID of the assessment to conduct
            patient_info: Basic information about the patient
            screening_result: Results from the screening phase
            
        Returns:
            Assessment instructions and questions
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Conduct assessment
        assessment_result = await self.assessment_agent.conduct_assessment(
            assessment_id=assessment_id,
            patient_info=patient_info,
            screening_result=screening_result,
            conversation_history=self.conversation_history[session_id]
        )
        
        # Update conversation history
        if assessment_result.get('choices') and len(assessment_result['choices']) > 0:
            self.conversation_history[session_id].append(
                {"role": "assistant", "content": assessment_result['choices'][0]['message']['content']}
            )
        
        return assessment_result
    
    async def process_assessment_responses(self, session_id: str, assessment_id: str, responses: List[int], patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the responses to an assessment.
        
        Args:
            session_id: Session ID
            assessment_id: ID of the assessment
            responses: List of numerical responses to the assessment questions
            patient_info: Basic information about the patient
            
        Returns:
            Processed assessment results and interpretation
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Process assessment responses
        assessment_results = await self.assessment_agent.process_assessment_results(
            assessment_id=assessment_id,
            responses=responses,
            patient_info=patient_info
        )
        
        # Update conversation history
        if assessment_results.get('interpretation', {}).get('choices') and len(assessment_results['interpretation']['choices']) > 0:
            self.conversation_history[session_id].append(
                {"role": "assistant", "content": assessment_results['interpretation']['choices'][0]['message']['content']}
            )
        
        return assessment_results
    
    async def generate_report(self, session_id: str, patient_info: Dict[str, Any], symptoms: List[str], screening_result: Dict[str, Any], assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a diagnosis report based on all collected information.
        
        Args:
            session_id: Session ID
            patient_info: Basic information about the patient
            symptoms: List of symptoms reported by the patient
            screening_result: Results from the screening phase
            assessment_results: Results from the assessment phase
            
        Returns:
            Diagnosis report
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Generate report
        report = await self.report_agent.generate_report(
            patient_info=patient_info,
            symptoms=symptoms,
            screening_result=screening_result,
            assessment_results=assessment_results,
            conversation_history=self.conversation_history[session_id]
        )
        
        # Clean up session data
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
        
        return report
    
    async def handle_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Handle a message in an ongoing conversation.
        
        Args:
            session_id: Session ID
            message: User message
            
        Returns:
            Response message
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Add user message to conversation history
        self.conversation_history[session_id].append({"role": "user", "content": message})
        
        # Generate a response based on the current stage
        # This is a simple response - in a real system, you would determine
        # which agent should handle this based on the current stage
        messages = [
            {"role": "system", "content": "You are a mental health chatbot assistant. Be empathetic, professional, and helpful."},
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history[session_id])
        
        response = await self.screening_agent._make_api_call(messages)
        
        # Update conversation history
        if response.get('choices') and len(response['choices']) > 0:
            self.conversation_history[session_id].append(
                {"role": "assistant", "content": response['choices'][0]['message']['content']}
            )
        
        return response
    
    # Legacy method for backward compatibility
    async def process_diagnosis(self, symptoms: List[str]) -> Dict[str, Any]:
        """
        Process a diagnosis request using the three-step process.
        
        Args:
            symptoms: List of symptoms reported by the patient
            
        Returns:
            Diagnosis results including screening, assessment, and report
        """
        # Create basic patient info
        patient_info = {
            "name": "Anonymous Patient",
            "age": None,
            "gender": None,
            "chief_complaints": symptoms
        }
        
        # Step 1: Screening
        screening_session = await self.start_session(patient_info, symptoms)
        session_id = screening_session["session_id"]
        screening_result = screening_session["screening_result"]
        
        # Get the recommended assessment (default to DASS-21)
        recommended_assessments = screening_result.get("recommended_assessments", ["DASS-21"])
        assessment_id = recommended_assessments[0] if recommended_assessments else "DASS-21"
        
        # Step 2: Assessment (simulate responses for automated testing)
        # In a real application, you would collect actual responses from the user
        assessment_info = await self.conduct_assessment(session_id, assessment_id, patient_info, screening_result)
        
        # Simulate random responses (0-3) for each question
        import random
        questions = assessment_info.get("assessment_details", {}).get("questions", [])
        simulated_responses = [random.randint(0, 3) for _ in range(len(questions))]
        
        # Process assessment responses
        assessment_results = await self.process_assessment_responses(session_id, assessment_id, simulated_responses, patient_info)
        
        # Step 3: Report Generation
        report_result = await self.generate_report(
            session_id,
            patient_info,
            symptoms,
            screening_result,
            assessment_results
        )
        
        return {
            "screening": screening_result,
            "assessment": assessment_results,
            "report": report_result
        } 