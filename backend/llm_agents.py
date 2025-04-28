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
import traceback
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("API_KEY", "sk-UnNXXoNG6qqa1RUl24zKrakQaHBeyxqkxEtaVwGbSrGlRQxl")
API_BASE = os.getenv("API_BASE", "https://xiaoai.plus/v1")
RATE_LIMIT_REQUESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 10  # seconds

if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

# Initialize OpenAI client with custom base URL
client = AsyncOpenAI(
    base_url=API_BASE,
    api_key=API_KEY
)

# Get the absolute path to the FAISS index directory
current_dir = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(current_dir, "faiss_index") 
print(f"FAISS index path: {FAISS_INDEX_PATH}")

# Check if the index files exist
faiss_file = os.path.join(FAISS_INDEX_PATH, "index.faiss")
pkl_file = os.path.join(FAISS_INDEX_PATH, "index.pkl")
if os.path.exists(faiss_file) and os.path.exists(pkl_file):
    print(f"Found FAISS index files: {faiss_file} and {pkl_file}")
else:
    print(f"WARNING: FAISS index files not found at {FAISS_INDEX_PATH}")
    print(f"Files in directory: {os.listdir(FAISS_INDEX_PATH) if os.path.exists(FAISS_INDEX_PATH) else 'Directory does not exist'}")

# --- Vector store initialization ---
embeddings_model = None
vector_store = None

try:
    # Import necessary modules
    from langchain_openai import OpenAIEmbeddings
    
    try:
        from langchain_community.vectorstores import FAISS
        print("Using langchain_community.vectorstores.FAISS")
    except ImportError:
        try:
            from langchain.vectorstores import FAISS
            print("Using langchain.vectorstores.FAISS")
        except ImportError:
            print("Could not import FAISS from either langchain_community or langchain")
            raise
    
    # Initialize embeddings model
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        openai_api_base=API_BASE,
        openai_api_key=API_KEY
    )
    print("OpenAIEmbeddings model initialized successfully.")
    
    # Load FAISS index
    try:
        print(f"Attempting to load FAISS index from: {FAISS_INDEX_PATH}")
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH, 
            embeddings_model
        )
        print("FAISS index loaded successfully.")
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        print(f"Detailed error: {traceback.format_exc()}")
        
        # Create a sample vector store for testing if loading fails
        from langchain.docstore.document import Document
        
        # Sample mental disorder descriptions
        sample_texts = [
            """{"name": "Major Depressive Disorder", "criteria": "A. Five (or more) of the following symptoms have been present during the same 2-week period and represent a change from previous functioning; at least one of the symptoms is either (1) depressed mood or (2) loss of interest or pleasure: 1. Depressed mood most of the day, nearly every day. 2. Markedly diminished interest or pleasure in all, or almost all, activities most of the day, nearly every day. 3. Significant weight loss when not dieting or weight gain, or decrease or increase in appetite nearly every day. 4. Insomnia or hypersomnia nearly every day. 5. Psychomotor agitation or retardation nearly every day. 6. Fatigue or loss of energy nearly every day. 7. Feelings of worthlessness or excessive or inappropriate guilt nearly every day. 8. Diminished ability to think or concentrate, or indecisiveness, nearly every day. 9. Recurrent thoughts of death, recurrent suicidal ideation without a specific plan, or a suicide attempt or a specific plan for committing suicide."}""",
            
            """{"name": "Generalized Anxiety Disorder", "criteria": "A. Excessive anxiety and worry (apprehensive expectation), occurring more days than not for at least 6 months, about a number of events or activities (such as work or school performance). B. The individual finds it difficult to control the worry. C. The anxiety and worry are associated with three (or more) of the following six symptoms (with at least some symptoms having been present for more days than not for the past 6 months): 1. Restlessness or feeling keyed up or on edge. 2. Being easily fatigued. 3. Difficulty concentrating or mind going blank. 4. Irritability. 5. Muscle tension. 6. Sleep disturbance (difficulty falling or staying asleep, or restless, unsatisfying sleep)."}""",
            
            """{"name": "Panic Disorder", "criteria": "A. Recurrent unexpected panic attacks. A panic attack is an abrupt surge of intense fear or intense discomfort that reaches a peak within minutes, and during which time four (or more) of the following symptoms occur: 1. Palpitations, pounding heart, or accelerated heart rate. 2. Sweating. 3. Trembling or shaking. 4. Sensations of shortness of breath or smothering. 5. Feelings of choking. 6. Chest pain or discomfort. 7. Nausea or abdominal distress. 8. Feeling dizzy, unsteady, light-headed, or faint. 9. Chills or heat sensations. 10. Paresthesias (numbness or tingling sensations). 11. Derealization (feelings of unreality) or depersonalization (being detached from oneself). 12. Fear of losing control or 'going crazy.' 13. Fear of dying."}""",
            
            """{"name": "Persistent Depressive Disorder", "criteria": "A. Depressed mood for most of the day, for more days than not, as indicated by either subjective account or observation by others, for at least 2 years. B. Presence, while depressed, of two (or more) of the following: 1. Poor appetite or overeating. 2. Insomnia or hypersomnia. 3. Low energy or fatigue. 4. Low self-esteem. 5. Poor concentration or difficulty making decisions. 6. Feelings of hopelessness."}""",
            
            """{"name": "Posttraumatic Stress Disorder", "criteria": "A. Exposure to actual or threatened death, serious injury, or sexual violence. B. Presence of one (or more) of the following intrusion symptoms associated with the traumatic event(s): 1. Recurrent, involuntary, and intrusive distressing memories. 2. Recurrent distressing dreams. 3. Dissociative reactions (e.g., flashbacks). 4. Intense or prolonged psychological distress at exposure to internal or external cues. 5. Marked physiological reactions to internal or external cues. C. Persistent avoidance of stimuli associated with the traumatic event(s). D. Negative alterations in cognitions and mood associated with the traumatic event(s). E. Marked alterations in arousal and reactivity associated with the traumatic event(s)."}""",
            
            """{"name": "Normal", "criteria": "The individual does not meet criteria for any mental disorder. Normal responses to stressors may include temporary anxiety, sadness, or stress that does not significantly impair daily functioning and resolves naturally. Common experiences include: 1. Temporary nervousness before events like exams or presentations. 2. Brief periods of sadness following disappointments. 3. Short-term sleep changes during stressful periods. 4. Appropriate emotional responses to life circumstances."}"""
        ]
        
        sample_docs = [Document(page_content=text) for text in sample_texts]
        vector_store = FAISS.from_documents(sample_docs, embeddings_model)
        print("Created sample vector store with basic mental disorder information.")

except Exception as e:
    print(f"Error initializing vector store: {e}")
    print(f"Detailed error: {traceback.format_exc()}")
    embeddings_model = None
    vector_store = None

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
    async def _make_api_call(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        await rate_limiter.acquire()
        try:
            async with asyncio.timeout(30):  # 30-second timeout
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=temperature
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

class RAGScreeningAgent(BaseAgent):
    """Screening agent that uses RAG to provide accurate mental health information."""
    
    async def search_database(self, query: str, k: int = 3) -> str:
        """Search the vector store and return formatted results."""
        print(f"Searching database with query: '{query}'")
        try:
            if vector_store is None:
                return "Error: Vector store not available."
            
            # Perform similarity search on the vector store
            docs = vector_store.similarity_search(query, k=k)
            
            # Format the results
            results = "\n".join([doc.page_content for doc in docs])
            return f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>"
        except Exception as e:
            print(f"Error during similarity search: {e}")
            return f"Error retrieving information: {str(e)}"
    
    async def screen_patient(self, patient_info: Dict[str, Any], symptoms: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Initial screening to gather patient information and identify potential mental health issues using RAG.
        
        Args:
            patient_info: Basic information about the patient
            symptoms: List of symptoms reported by the patient
            conversation_history: Previous conversation history, if any
            
        Returns:
            Screening results including potential issues and JSON output with diagnosis
        """
        symptom_text = ", ".join(symptoms) if symptoms else "No specific symptoms reported"
        
        # First, search the database for relevant mental disorders based on symptoms
        search_query = f"Mental disorders with symptoms including: {symptom_text}"
        retrieval_results = await self.search_database(search_query)
        
        # Create the system prompt
        system_prompt = """Your Name is Dr. Mind, a professional mental disorder screening specialist. 

step by step process:
1. Begin by asking for the patient's name and age in a friendly, professional manner.
2. Ask about their feelings, physical symptoms, and the duration of these symptoms.
3. After collecting initial information, use the search_document_database tool to query the mental disorders database with specific symptoms described.
4. Analyze if the patient's symptoms fulfill the diagnostic criteria from the retrieved information.
5. Ask follow-up questions if more information is needed to confirm or rule out a diagnosis.
6. If the criteria are fulfilled or some main criteria are met, go to point 10. and end the chat with a diagnosis in JSON format.
7. If symptoms don't match the first retrieval result, create a new query based on updated patient information and search again.
8. Limit database searches to a maximum of 3 times per conversation.
9. After 3 searches, provide the most matching diagnosis based on the conversation history, even if not all criteria are met.
10. End the conversation with one JSON output only, remove all other text. : {"result":["disorder name"], "probabilities":[0.X]} (where X is a number between 0-9 representing how confident you are in the diagnosis).
"""
        
        # Initial message
        initial_message = f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Chief complaints: {symptom_text}

Here is information from the mental disorders database:
{retrieval_results}

Based on this information, please introduce yourself and ask some initial questions to understand the patient's symptoms better.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": initial_message}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
        
        response = await self._make_api_call(messages)
        
        # Check if the response contains JSON output
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Try to extract JSON from the response
        json_result = None
        try:
            # Find patterns like {"result":["disorder"], "probabilities":[0.8]}
            import re
            json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1)
                json_result = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON result: {e}")
        
        # Add RAG results and extracted JSON to the response
        response["rag_results"] = retrieval_results
        response["diagnosis_json"] = json_result
        
        return response

# Legacy ScreeningAgent - keeping for backward compatibility
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
    """Multi-agent mental health chatbot that conducts screening, assessment, and generates reports."""
    
    def __init__(self):
        self.sessions = {}  # Session storage
        self.screening_agent = RAGScreeningAgent()
        self.assessment_agent = AssessmentAgent()
        self.report_agent = ReportAgent()

    async def start_session(self, patient_info: Dict[str, Any], symptoms: List[str]) -> Dict[str, Any]:
        """
        Start a new chatbot session with screening.
        
        Args:
            patient_info: Information about the patient
            symptoms: List of symptoms or chief complaints
            
        Returns:
            Session information including ID and initial message
        """
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session with screening
        screening_result = await self.screening_agent.screen_patient(
            patient_info=patient_info,
            symptoms=symptoms
        )
        
        # Store session data
        self.sessions[session_id] = {
            "id": session_id,
            "patient_info": patient_info,
            "symptoms": symptoms,
            "status": "screening",
            "screening_result": screening_result,
            "conversation_history": [
                {"role": "assistant", "content": screening_result["choices"][0]["message"]["content"]}
            ],
            "searches_performed": 1,  # Track RAG searches
            "assessment_results": {},
            "report": None
        }
        
        return {
            "session_id": session_id,
            "screening_result": screening_result,
            "message": screening_result["choices"][0]["message"]["content"]
        }
    
    async def _determine_next_assessment(self, diagnosis_json: Dict[str, Any]) -> str:
        """Determine which assessment to use based on screening results."""
        if not diagnosis_json or "result" not in diagnosis_json:
            return "DASS-21"  # Default assessment
            
        disorders = diagnosis_json.get("result", [])
        
        # Map disorders to appropriate assessments
        ptsd_indicators = ["Posttraumatic Stress Disorder", "PTSD"]
        depression_anxiety_indicators = [
            "Major Depressive Disorder", 
            "Persistent Depressive Disorder", 
            "Generalized Anxiety Disorder", 
            "Panic Disorder"
        ]
        
        # Check if PTSD is in the results
        for disorder in disorders:
            if any(indicator in disorder for indicator in ptsd_indicators):
                return "PCL-5"
                
        # Check for depression/anxiety disorders
        for disorder in disorders:
            if any(indicator in disorder for indicator in depression_anxiety_indicators):
                return "DASS-21"
                
        # Default to DASS-21 for any other disorder
        return "DASS-21"
    
    async def handle_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Handle an incoming message in the conversation flow.
        
        Args:
            session_id: The session identifier
            message: The user message
            
        Returns:
            Response information including message and any assessment data
        """
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = self.sessions[session_id]
        
        # Add the user message to conversation history
        session["conversation_history"].append({"role": "user", "content": message})
        
        # Determine the current state and handle accordingly
        current_status = session.get("status", "screening")
        
        if current_status == "screening":
            # Continue with screening until we get diagnosis JSON result
            # Perform a new RAG search if needed
            if "I need more information" in message or "symptoms" in message.lower() or session["searches_performed"] < 3:
                # Extract symptoms from the message
                symptom_extraction_messages = [
                    {"role": "system", "content": "You are an AI assistant that extracts relevant symptoms from patient messages."},
                    {"role": "user", "content": f"Extract the key symptoms or concerns from this patient message. Return ONLY the symptoms as a comma-separated list, with no additional text: {message}"}
                ]
                symptom_extraction = await self.screening_agent._make_api_call(symptom_extraction_messages)
                symptom_text = symptom_extraction["choices"][0]["message"]["content"]
                
                # Perform a new RAG search with refined symptoms
                retrieval_results = await self.screening_agent.search_database(symptom_text)
                session["searches_performed"] += 1
                
                # Prepare messages for the agent, including history and new retrieval
                agent_messages = [
                    {"role": "system", "content": """Your Name is Dr. Mind, a professional mental disorder screening specialist. 
Continue the mental health diagnosis conversation. Use the patient's symptoms to match against diagnostic criteria. If you have sufficient information, provide a diagnosis in JSON format {"result":["disorder name"], "probabilities":[0.X]} without any other text. If you need more information, continue asking relevant questions."""},
                ]
                
                # Add existing conversation history
                agent_messages.extend(session["conversation_history"][:-1])  # All except the most recent user message
                
                # Add the search results context and the latest user message
                agent_messages.append({"role": "user", "content": f"""Here is new information from the mental disorders database based on the patient's latest message:
{retrieval_results}

The patient's latest message is: {message}

Based on all information so far, continue the conversation. If you have enough information for a diagnosis, provide ONLY a JSON output in the format: {{"result":["disorder name"], "probabilities":[0.X]}} with no other text."""})
                
                # Call the agent
                response = await self.screening_agent._make_api_call(agent_messages)
                content = response["choices"][0]["message"]["content"]
                
                # Try to extract JSON from the response
                json_result = None
                try:
                    import re
                    json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
                    if json_match:
                        json_str = json_match.group(1)
                        json_result = json.loads(json_str)
                        # If we got a JSON result, we're done with screening
                        session["status"] = "screening_complete"
                        session["diagnosis_json"] = json_result
                        
                        # Determine which assessment to use next
                        recommended_assessment = await self._determine_next_assessment(json_result)
                        session["recommended_assessment"] = recommended_assessment
                except Exception as e:
                    print(f"Error parsing JSON result: {e}")
                
                # Store response in conversation history
                session["conversation_history"].append({"role": "assistant", "content": content})
                
                # Return response with assessment info if screening is complete
                if session["status"] == "screening_complete":
                    return {
                        "message": content,
                        "status": "screening_complete",
                        "diagnosis_json": json_result,
                        "recommended_assessment": session["recommended_assessment"]
                    }
                else:
                    return {"message": content}
            
            # If we've reached the max number of searches, try to generate a diagnosis
            if session["searches_performed"] >= 3:
                # Attempt to generate a final diagnosis based on all conversation history
                diagnosis_prompt = [
                    {"role": "system", "content": "You are a mental health professional who needs to make a diagnosis based on the conversation history. Provide your diagnosis in JSON format: {\"result\":[\"disorder name\"], \"probabilities\":[0.X]} with no other text."},
                    {"role": "user", "content": f"Here is the conversation history between a mental health chatbot and a patient. Based on this information, determine the most likely diagnosis:\n\n{json.dumps(session['conversation_history'])}"}
                ]
                
                diagnosis_response = await self.screening_agent._make_api_call(diagnosis_prompt)
                diagnosis_content = diagnosis_response["choices"][0]["message"]["content"]
                
                # Try to extract JSON from the response
                json_result = None
                try:
                    import re
                    json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', diagnosis_content)
                    if json_match:
                        json_str = json_match.group(1)
                        json_result = json.loads(json_str)
                except Exception as e:
                    print(f"Error parsing JSON result: {e}")
                    # If we can't parse JSON, create a basic one
                    json_result = {"result": ["Unspecified Disorder"], "probabilities": [0.5]}
                
                # Update session status and store diagnosis result
                session["status"] = "screening_complete"
                session["diagnosis_json"] = json_result
                
                # Determine which assessment to use next
                recommended_assessment = await self._determine_next_assessment(json_result)
                session["recommended_assessment"] = recommended_assessment
                
                # Add final diagnostic message to conversation history
                final_message = f"Based on our conversation, I've completed my initial assessment. {diagnosis_content}"
                session["conversation_history"].append({"role": "assistant", "content": final_message})
                
                return {
                    "message": final_message,
                    "status": "screening_complete",
                    "diagnosis_json": json_result,
                    "recommended_assessment": recommended_assessment
                }
        
        elif current_status == "screening_complete" or current_status == "assessment":
            # If we're waiting for the client to start an assessment, just respond conversationally
            response_messages = [
                {"role": "system", "content": "You are a mental health professional. The screening phase is complete, and an assessment has been recommended. Respond to the patient's message while encouraging them to proceed with the recommended assessment for more detailed insights."},
                {"role": "user", "content": f"The patient has completed screening, and the {session.get('recommended_assessment', 'DASS-21')} assessment is recommended. The patient says: {message}"}
            ]
            
            response = await self.screening_agent._make_api_call(response_messages)
            content = response["choices"][0]["message"]["content"]
            
            # Store response in conversation history
            session["conversation_history"].append({"role": "assistant", "content": content})
            
            return {
                "message": content,
                "status": session["status"],
                "recommended_assessment": session.get("recommended_assessment", "DASS-21")
            }
            
        elif current_status == "assessment_complete":
            # If assessment is complete, we're waiting to generate the report
            response_messages = [
                {"role": "system", "content": "You are a mental health professional. The patient has completed both screening and assessment. Respond to their message while mentioning that you're preparing their report."},
                {"role": "user", "content": f"The patient has completed the assessment. They say: {message}"}
            ]
            
            response = await self.screening_agent._make_api_call(response_messages)
            content = response["choices"][0]["message"]["content"]
            
            # Store response in conversation history
            session["conversation_history"].append({"role": "assistant", "content": content})
            
            return {
                "message": content,
                "status": "assessment_complete"
            }
            
        else:
            # Default fallback for any other state
            response_messages = [
                {"role": "system", "content": "You are a mental health chatbot assistant. Respond helpfully to the patient's message."},
                {"role": "user", "content": message}
            ]
            
            response = await self.screening_agent._make_api_call(response_messages)
            content = response["choices"][0]["message"]["content"]
            
            # Store response in conversation history
            session["conversation_history"].append({"role": "assistant", "content": content})
            
            return {"message": content}
    
    async def conduct_assessment(self, session_id: str, assessment_id: str, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a standardized assessment.
        
        Args:
            session_id: The session identifier
            assessment_id: The ID of the assessment to conduct
            patient_info: Information about the patient
            
        Returns:
            Assessment initialization data
        """
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = self.sessions[session_id]
        
        # Get or create patient info
        if not patient_info and "patient_info" in session:
            patient_info = session["patient_info"]
        
        # Conduct the assessment
        assessment_result = await self.assessment_agent.conduct_assessment(
            assessment_id=assessment_id,
            patient_info=patient_info,
            screening_result=session["screening_result"],
            conversation_history=session["conversation_history"]
        )
        
        # Update session status
        session["status"] = "assessment"
        session["current_assessment"] = assessment_id
        
        return assessment_result
    
    async def process_assessment_responses(self, session_id: str, assessment_id: str, responses: List[int], patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the responses to an assessment.
        
        Args:
            session_id: The session identifier
            assessment_id: The ID of the assessment
            responses: List of numerical responses to the assessment questions
            patient_info: Information about the patient
            
        Returns:
            Processed assessment results
        """
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = self.sessions[session_id]
        
        # Process the assessment results
        result = await self.assessment_agent.process_assessment_results(
            assessment_id=assessment_id,
            responses=responses,
            patient_info=patient_info
        )
        
        # Store results in session
        session["assessment_results"][assessment_id] = result
        session["status"] = "assessment_complete"
        
        return result
    
    async def generate_report(self, session_id: str, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive diagnostic report.
        
        Args:
            session_id: The session identifier
            patient_info: Complete patient information for the report
            
        Returns:
            Generated diagnostic report
        """
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = self.sessions[session_id]
        
        # Generate the report
        report = await self.report_agent.generate_report(
            patient_info=patient_info,
            symptoms=session["symptoms"],
            screening_result=session["screening_result"],
            assessment_results=session["assessment_results"],
            conversation_history=session["conversation_history"]
        )
        
        # Store report in session
        session["report"] = report
        session["status"] = "complete"
        
        return report
    
    async def process_diagnosis(self, symptoms: List[str]) -> Dict[str, Any]:
        """Legacy method for compatibility with old API."""
        # ... existing code ... 