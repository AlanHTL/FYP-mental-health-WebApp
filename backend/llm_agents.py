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

# Add LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool

# System prompts for the various agents
SCREENING_SYSTEM_PROMPT = """Your Name is Dr. Mind, a professional mental disorder screening specialist. Your goal is to conduct a mental health screening conversation with the user to determine if they might be experiencing symptoms of a mental health disorder.

Follow these guidelines:
1. Ask relevant questions to understand their symptoms and concerns
2. Be empathetic and professional in your responses
3. When you have enough information, provide a diagnosis in the following JSON format:
   {"result":["disorder name"], "probabilities":[0.8]}
   
You may list multiple potential disorders with their respective probabilities based on the conversation.
Only provide the JSON when you're confident you have enough information for a preliminary diagnosis.
Otherwise, continue asking questions to gather more information."""

ASSESSMENT_SYSTEM_PROMPT = """Your Name is Dr. Mind, a professional mental health assessment specialist. Your goal is to administer a formal assessment to measure the severity of the user's symptoms. 

Follow these guidelines:
1. Present one question at a time from the assessment
2. Explain the rating scale for each question (e.g., 0-3 for severity)
3. Accept the user's numerical rating and move to the next question
4. Be empathetic and professional in your responses
5. Once all questions are answered, calculate the score based on the assessment guidelines

Do not provide an interpretation of the results - just collect the responses."""

REPORT_SYSTEM_PROMPT = """Your Name is Dr. Mind, a professional mental health report specialist. Your goal is to generate a comprehensive mental health report based on the screening conversation, assessment results, and other information provided.

Follow these guidelines:
1. Summarize the key symptoms and concerns reported
2. Provide an interpretation of the assessment scores
3. Offer general recommendations for next steps
4. Use professional but accessible language
5. Be empathetic and constructive in your analysis

The report should be well-structured with clear sections for: Summary, Assessment Results, Interpretation, and Recommendations."""

load_dotenv()

# Use environment variables for OpenAI API
API_KEY = os.getenv("OPENAI_API_KEY", "sk-UnNXXoNG6qqa1RUl24zKrakQaHBeyxqkxEtaVwGbSrGlRQxl")
API_BASE = os.getenv("OPENAI_API_BASE", "https://xiaoai.plus/v1")
RATE_LIMIT_REQUESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 10  # seconds

if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Set environment variables for LangChain
os.environ["OPENAI_API_KEY"] = API_KEY
os.environ["OPENAI_API_BASE"] = API_BASE

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
            embeddings_model,
            allow_dangerous_deserialization=True
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
    """Screening agent that uses RAG to provide accurate mental health information using OpenAI function calling."""
    
    def __init__(self):
        self.agent_executor = None
        self.chat_model = None
        self.retriever_tool = None
        self.conversation_memory_store = {}
        self.initialize_agent()
    
    def search_database(self, query: str, k: int = 3) -> str:
        """Search the vector store, print status, and return formatted results."""
        with open("search_log.txt", "a") as log_file:
            log_file.write(f"\n\n[{datetime.now()}] SEARCH QUERY: '{query}'\n")
            print(f"DEBUG: Searching database with query: '{query}'")
            
            try:
                if vector_store is None:
                    msg = "Error: Vector store not available."
                    log_file.write(f"ERROR: {msg}\n")
                    print(msg)
                    return msg
                
                # Perform similarity search directly on the vector store
                docs = vector_store.similarity_search(query, k=k)
                
                # For debugging, print each document content with clear separators
                print("DEBUG: RETRIEVAL RESULTS ----------------")
                log_file.write("RETRIEVAL RESULTS ----------------\n")
                
                for i, doc in enumerate(docs):
                    print(f"DEBUG: RESULT {i+1}:")
                    print(f"DEBUG: {doc.page_content}")
                    print("DEBUG: -----------------------------------")
                    
                    log_file.write(f"RESULT {i+1}:\n")
                    log_file.write(f"{doc.page_content}\n")
                    log_file.write("-----------------------------------\n")
                
                # Format the results as a single string
                results = "\n".join([doc.page_content for doc in docs])
                formatted_result = f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>"
                
                log_file.write(f"RETURNING {len(docs)} RESULTS\n")
                return formatted_result
                
            except Exception as e:
                error_msg = f"Error during similarity search: {str(e)}"
                log_file.write(f"ERROR: {error_msg}\n")
                log_file.write(f"TRACEBACK: {traceback.format_exc()}\n")
                print(error_msg)
                print(traceback.format_exc())
                return f"Error retrieving information: {str(e)}"
    
    def initialize_agent(self):
        """Initialize the LangChain agent with tools and prompt."""
        try:
            # Initialize chat model using environment variables
            self.chat_model = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            print("ChatOpenAI model initialized successfully.")
            
            # Create the retriever tool
            self.retriever_tool = Tool(
                name="search_document_database",
                description="Searches and returns relevant information from the document database based on the user query.",
                func=self.search_database,
                return_direct=False,  # Let the agent decide how to incorporate the results
            )
            print("Retriever tool created successfully.")
            
            # Define the prompt template for the agent - using the exact provided prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Your Name is Dr. Mind, a professional mental disorder screening specialist. 

step by step process:
1. Begin by asking for the patient's name and age in a friendly, professional manner.
2. Ask about their feelings, physical symptoms, and the duration of these symptoms.
3. IMPORTANT: After collecting initial information, you MUST use the search_document_database tool to query the mental disorders database with specific symptoms described.
4. Analyze if the patient's symptoms fulfill the diagnostic criteria from the retrieved information.
5. Ask follow-up questions if more information is needed to confirm or rule out a diagnosis.
6. If the criteria are fulfilled or some main criteria are met, go to point 10. and end the chat with a diagnosis in JSON format.
7. If symptoms don't match the first retrieval result, create a new query based on updated patient information and search again.
8. Limit database searches to a maximum of 3 times per conversation.
9. After 3 searches, provide the most matching diagnosis based on the conversation history, even if not all criteria are met.
10. End the conversation with one JSON output only, remove all other text. : {{"result":["disorder name"], "probabilities":[0.X]}} (where X is a number between 0-9 representing how confident you are in the diagnosis).

IMPORTANT: You MUST use the search_document_database tool at least once during each patient conversation. This tool connects to our mental health disorder database, which contains accurate diagnostic criteria that you need to evaluate patients properly. Always use the tool with a focused search query containing the most prominent symptoms.
     
Here are examples of how to end conversations with JSON output only:

Example 1:
Patient: I've been feeling really down for the past few months, can't sleep, and lost interest in everything.
Dr. Mind: Let me ask you a few questions to understand better. Have you been feeling sad or empty most of the day?
Patient: Yes, almost every day.
Dr. Mind: Have you lost interest in activities you used to enjoy?
Patient: Yes, I don't enjoy anything anymore.
Dr. Mind: How has your sleep been?
Patient: I can't sleep at night, but I sleep too much during the day.
Dr. Mind: Have you had any thoughts about death or suicide?
Patient: Yes, sometimes I think about it.
Dr. Mind: {{"result":["Major Depressive Disorder"], "probabilities":[0.8]}}

Example 2:
Patient: I keep having these thoughts that I can't control, and I have to wash my hands many times.
Dr. Mind: Can you tell me more about these thoughts?
Patient: They're about germs and contamination, and I can't stop thinking about them.
Dr. Mind: How many times do you wash your hands in a day?
Patient: At least 50 times, sometimes more.
Dr. Mind: Do you feel you have to do this to prevent something bad from happening?
Patient: Yes, I feel like if I don't wash my hands, something terrible will happen.
Dr. Mind: {{"result":["Obsessive-Compulsive Disorder"], "probabilities":[0.9]}}

Example 3:
Patient: I am a bit nervous about my exam tomorrow.
Dr. Mind: Do you find it hard to control your worry?
Patient: No, I can control it.
Dr. Mind: Do you have any physical symptoms, like trembling or sweating?
Patient: No, I don't have any physical symptoms.
Dr. Mind: Have you been having trouble sleeping?
Patient: No, I sleep well.
Dr. Mind: {{"result":["Normal"], "probabilities":[0.8]}}

Guidelines:
- Use a chain-of-thought approach: think step by step and explain your reasoning.
- Be compassionate and professional in your communication.
- Ask one question at a time to avoid overwhelming the patient, e.g. DO NOT: ("could you please share if you have been feeling sad or empty most of the day, lost interest in activities you used to enjoy, or have thoughts of worthlessness or guilt?)  DO: ("have you been feeling sad or empty most of the day?", DO:"what activities you are interested in?",DO: "Do you still enjoy (activity mentioned by the patient) now?", DO:"have you had thoughts of worthlessness or guilt?")
- When searching the database, create focused queries based on the most prominent symptoms.
- Keep track of how many times you've queried the database in this conversation.
- Before making a diagnosis, verify that the patient meets the required criteria from DSM-5.
- Do not mention the DSM-5 in your response, just use the disorder name.
- For emergency situations or suicidal actions, provide immediate help information: full_text("*\n1. *If you are in an immediately dangerous situation (such as on a rooftop, bridge, or with means of harm):\n- Move to a safe location immediately\n- Call emergency services: 999\n- Stay on the line with emergency services\n\n2. **For immediate support:\n- Go to your nearest emergency room/A&E department\n- Call The Samaritans hotline (Multilingual): (852) 2896 0000\n- Call Suicide Prevention Service hotline (Cantonese): (852) 2382 0000\n\nAre you currently in a safe location?* If not, please seek immediate help using the emergency contacts above.\n*** Do you want to keep going with the screening?")
- Once you have enough information for a diagnosis, End with a JSON output, do not include any other text, if have any, remove it.
- JSON format: {{"result":["disorder name"], "probabilities":[0.X]}} (where X is a number between 0-9 representing how confident you are in the diagnosis).
"""),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # Create the agent and executor
            tools = [self.retriever_tool]
            agent = create_openai_functions_agent(self.chat_model, tools, prompt)
            self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            print("Agent Executor created successfully.")
            
        except Exception as e:
            print(f"Error initializing agent: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
    
    # Custom chat message history class for memory
    class InMemoryChatMessageHistory(BaseChatMessageHistory):
        """Simple in-memory implementation of chat message history."""
        
        def __init__(self, session_id: str):
            self.session_id = session_id
            self._messages = []
        
        def add_message(self, message):
            """Add a message to the history."""
            self._messages.append(message)
            
        def clear(self):
            """Clear the message history."""
            self._messages = []
        
        @property
        def messages(self):
            return self._messages
    
    def get_memory(self, session_id: str):
        """Retrieves or creates memory for a session."""
        if session_id not in self.conversation_memory_store:
            # Each session gets its own memory instance
            self.conversation_memory_store[session_id] = self.InMemoryChatMessageHistory(session_id=session_id)
            print(f"Created new chat history for session_id: {session_id}")
        return self.conversation_memory_store[session_id]
        
    async def screen_patient(self, patient_info: Dict[str, Any], symptoms: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Initial screening to gather patient information and identify potential mental health issues using RAG with LangChain.
        
        Args:
            patient_info: Basic information about the patient
            symptoms: List of symptoms reported by the patient
            conversation_history: Previous conversation history, if any
            
        Returns:
            Screening results including potential issues and JSON output with diagnosis
        """
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Prepare the input
        symptom_text = ", ".join(symptoms) if symptoms else "No specific symptoms reported"
        
        initial_message = f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Chief complaints: {symptom_text}

**Start with a warm greeting to the patient.** Then, introduce yourself as Dr. Mind and begin asking initial questions about their symptoms. 
After collecting some initial information, remember to use the search_document_database tool with a focused query to find relevant mental disorder information.
"""
        
        try:
            # Set up the history-aware agent
            agent_with_history = RunnableWithMessageHistory(
                self.agent_executor,
                self.get_memory,
                input_messages_key="input",
                history_messages_key="chat_history",
            )
            
            # Configuration for the agent invocation, including the session ID for memory
            config = {"configurable": {"session_id": session_id}}
            
            # Use the agent to process the message
            response = await agent_with_history.ainvoke({"input": initial_message}, config=config)
            
            # Get the response content as string
            content = response.get("output", "")
            
            # Try to extract JSON from the response
            json_result = None
            try:
                import re
                # First try to find JSON with both result and probabilities
                json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
                if not json_match:
                    # Try to find any JSON object
                    json_match = re.search(r'({[\s\S]*?})', content)
                if json_match:
                    json_str = json_match.group(1)
                    json_result = json.loads(json_str)
                    # Ensure the JSON has the required fields
                    if "result" not in json_result:
                        json_result["result"] = ["Unspecified"]
                    if "probabilities" not in json_result:
                        json_result["probabilities"] = [1.0]
                    # If we got a JSON result, we're done with screening
                    session["status"] = "screening_complete"
                    session["diagnosis_json"] = json_result
                    session["screening_result"] = json_result  # Add for compatibility
                    
                    # Determine which assessment to use next
                    recommended_assessment = await self._determine_next_assessment(json_result)
                    session["recommended_assessment"] = recommended_assessment
            except Exception as e:
                print(f"Error parsing JSON result: {e}")
            
            # Format the response
            result = {
                "choices": [{"message": {"content": content}}],
                "rag_results": "Screening initialized",
                "diagnosis_json": json_result
            }
            
            return result
            
        except Exception as e:
            print(f"Error in agent execution: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            return await self._fallback_screening(patient_info, symptoms, conversation_history)
    
    async def _fallback_screening(self, patient_info: Dict[str, Any], symptoms: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Fallback method that uses direct API calls if LangChain fails."""
        print("Using fallback screening method with direct API calls")
        
        symptom_text = ", ".join(symptoms) if symptoms else "No specific symptoms reported"
        
        # First, search the database for relevant mental disorders based on symptoms
        search_query = f"Mental disorders with symptoms including: {symptom_text}"
        retrieval_results = self.search_database(search_query)
        
        # Create the system prompt
        system_prompt = """Your Name is Dr. Mind, a professional mental disorder screening specialist.

Follow these steps:
1. Introduce yourself and ask for patient's name and age in a friendly manner
2. Ask about feelings, physical symptoms, and duration of symptoms
3. Analyze symptoms and match against disorder criteria
4. Ask follow-up questions when more information is needed
5. Make a diagnosis when criteria are met
6. End with only a JSON diagnosis like: {"result":["Disorder Name"], "probabilities":[0.8]}

Remember to:
- Be compassionate and professional
- Ask one question at a time
- Only use disorder names found in the database
- For emergencies, provide emergency contact information
- Only include the JSON at the very end, with no other text"""
        
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
            # First try to find JSON with both result and probabilities
            json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
            if not json_match:
                # Try to find any JSON object
                json_match = re.search(r'({[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1)
                json_result = json.loads(json_str)
                # Ensure the JSON has the required fields
                if "result" not in json_result:
                    json_result["result"] = ["Unspecified"]
                if "probabilities" not in json_result:
                    json_result["probabilities"] = [1.0]
                # If we got a JSON result, we're done with screening
                session["status"] = "screening_complete"
                session["diagnosis_json"] = json_result
                session["screening_result"] = json_result  # Add for compatibility
                
                # Determine which assessment to use next
                recommended_assessment = await self._determine_next_assessment(json_result)
                session["recommended_assessment"] = recommended_assessment
        except Exception as e:
            print(f"Error parsing JSON result: {e}")
        
        # Add RAG results and extracted JSON to the response
        response["rag_results"] = retrieval_results
        response["diagnosis_json"] = json_result
        
        return response
    
class MentalHealthChatbot:
    """Multi-agent mental health chatbot that conducts screening, assessment, and generates reports."""
    
    def __init__(self):
        self.sessions = {}  # Session storage
        self.screening_agent = RAGScreeningAgent()
        self.assessment_agent = AssessmentAgent()
        self.report_agent = ReportAgent()
        
        # Initialize the screening agent when the chatbot is created
        try:
            if not self.screening_agent.agent_executor:
                self.screening_agent.initialize_agent()
        except Exception as e:
            print(f"Error initializing screening agent during chatbot creation: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            print("The chatbot will use fallback methods if the agent fails to initialize.")

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
        
        try:
            print(f"Starting new session {session_id} for patient: {patient_info.get('name', 'Unknown')}")
            # Initialize session with screening using the agent
            if self.screening_agent.agent_executor:
                # Prepare the input
                symptom_text = ", ".join(symptoms) if symptoms else "No specific symptoms reported"
                
                initial_message = f"""Patient Information:
Name: {patient_info.get('name', 'Unknown')}
Age: {patient_info.get('age', 'Unknown')}
Gender: {patient_info.get('gender', 'Unknown')}

Chief complaints: {symptom_text}

**Start with a warm greeting to the patient.** Then, introduce yourself as Dr. Mind and begin asking initial questions about their symptoms. 
After collecting some initial information, remember to use the search_document_database tool with a focused query to find relevant mental disorder information.
"""
                # Set up the history-aware agent
                agent_with_history = RunnableWithMessageHistory(
                    self.screening_agent.agent_executor,
                    self.screening_agent.get_memory,
                    input_messages_key="input",
                    history_messages_key="chat_history",
                )
                
                # Configuration for the agent invocation, including the session ID for memory
                config = {"configurable": {"session_id": session_id}}
                
                # Use the agent to process the message
                response = await agent_with_history.ainvoke({"input": initial_message}, config=config)
                
                # Get the response content
                content = response.get("output", "")
                
                # Try to extract JSON from the response (unlikely in first interaction)
                json_result = None
                try:
                    import re
                    # First try to find JSON with both result and probabilities
                    json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
                    if not json_match:
                        # Try to find any JSON object
                        json_match = re.search(r'({[\s\S]*?})', content)
                    if json_match:
                        json_str = json_match.group(1)
                        json_result = json.loads(json_str)
                        # Ensure the JSON has the required fields
                        if "result" not in json_result:
                            json_result["result"] = ["Unspecified"]
                        if "probabilities" not in json_result:
                            json_result["probabilities"] = [1.0]
                        # If we got a JSON result, we're done with screening
                        session["status"] = "screening_complete"
                        session["diagnosis_json"] = json_result
                        session["screening_result"] = json_result  # Add for compatibility
                        
                        # Determine which assessment to use next
                        recommended_assessment = await self._determine_next_assessment(json_result)
                        session["recommended_assessment"] = recommended_assessment
                except Exception as e:
                    print(f"Error parsing JSON result: {e}")
                    
                # Store session data
                self.sessions[session_id] = {
                    "id": session_id,
                    "patient_info": patient_info,
                    "symptoms": symptoms,
                    "status": "screening",
                    "screening_result": {"choices": [{"message": {"content": content}}]},
                    "conversation_history": [
                        {"role": "assistant", "content": content}
                    ],
                    "assessment_results": {},
                    "report": None,
                    "diagnosis_json": json_result
                }
                
                return {
                    "session_id": session_id,
                    "message": content
                }
            else:
                # Fall back to the original method if agent not available
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
        except Exception as e:
            print(f"Error starting session: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            
            # Fall back to the original method
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
            # For screening, we now use the agent for tool calling
            try:
                print(f"\nDEBUG: handle_message - SESSION {session_id} - STATUS: {current_status}")
                print(f"DEBUG: handle_message - USER MESSAGE: {message}")
                
                # Set up the history-aware agent
                agent_with_history = RunnableWithMessageHistory(
                    self.screening_agent.agent_executor,
                    self.screening_agent.get_memory,
                    input_messages_key="input",
                    history_messages_key="chat_history",
                )
                
                # Configuration for the agent invocation, including the session ID for memory
                config = {"configurable": {"session_id": session_id}}
                
                print(f"DEBUG: handle_message - Invoking agent for session {session_id}...")
                # Use the agent to process the message
                response = await agent_with_history.ainvoke({"input": message}, config=config)
                
                print(f"DEBUG: handle_message - RAW AGENT RESPONSE for session {session_id}: {response}")
                
                # Get the response content
                content = response.get("output", "")
                print(f"DEBUG: handle_message - Parsed content: {content}")
                
                # Try to extract JSON from the response
                json_result = None
                try:
                    import re
                    # First try to find JSON with both result and probabilities
                    json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
                    if not json_match:
                        # Try to find any JSON object
                        json_match = re.search(r'({[\s\S]*?})', content)
                    if json_match:
                        json_str = json_match.group(1)
                        json_result = json.loads(json_str)
                        # Ensure the JSON has the required fields
                        if "result" not in json_result:
                            json_result["result"] = ["Unspecified"]
                        if "probabilities" not in json_result:
                            json_result["probabilities"] = [1.0]
                        # If we got a JSON result, we're done with screening
                        session["status"] = "screening_complete"
                        session["diagnosis_json"] = json_result
                        session["screening_result"] = json_result  # Add for compatibility
                        
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
                    
            except Exception as e:
                print(f"Error using agent for screening: {e}")
                print(f"Detailed error: {traceback.format_exc()}")
                
                # Fall back to the previous method if agent fails
                return await self._fallback_handle_screening_message(session_id, message)
                
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
        # Create a temporary session just for this diagnosis
        patient_info = {"name": "Anonymous", "age": "Unknown", "gender": "Unknown"}
        session_data = await self.start_session(patient_info, symptoms)
        return session_data

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

    async def _fallback_handle_screening_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Fallback method for handling screening messages when the agent fails.
        """
        # Get the session
        session = self.sessions.get(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Add user message to conversation history
        session["conversation_history"].append({"role": "user", "content": message})
        
        # Construct messages for the screening conversation
        messages = [
            {"role": "system", "content": SCREENING_SYSTEM_PROMPT},
        ]
        
        # Add conversation history
        for msg in session["conversation_history"]:
            messages.append(msg)
        
        # Make API call to get response
        try:
            response = await self.screening_agent._make_api_call(messages)
            content = response["choices"][0]["message"]["content"]
            
            # Store response in conversation history
            session["conversation_history"].append({"role": "assistant", "content": content})
            
            # Try to extract JSON diagnosis from the response
            json_result = None
            try:
                import re
                # First try to find JSON with both result and probabilities
                json_match = re.search(r'({[\s\S]*?"result"[\s\S]*?"probabilities"[\s\S]*?})', content)
                if not json_match:
                    # Try to find any JSON object
                    json_match = re.search(r'({[\s\S]*?})', content)
                if json_match:
                    json_str = json_match.group(1)
                    json_result = json.loads(json_str)
                    # Ensure the JSON has the required fields
                    if "result" not in json_result:
                        json_result["result"] = ["Unspecified"]
                    if "probabilities" not in json_result:
                        json_result["probabilities"] = [1.0]
                    # If we got a JSON result, we're done with screening
                    session["status"] = "screening_complete"
                    session["diagnosis_json"] = json_result
                    session["screening_result"] = json_result  # Add for compatibility
                    
                    # Determine which assessment to use next
                    recommended_assessment = await self._determine_next_assessment(json_result)
                    session["recommended_assessment"] = recommended_assessment
            except Exception as e:
                print(f"Error parsing JSON result: {e}")
            
            # Return response with assessment info if screening is complete
            if session.get("status") == "screening_complete":
                return {
                    "message": content,
                    "status": "screening_complete",
                    "diagnosis_json": json_result,
                    "recommended_assessment": session["recommended_assessment"]
                }
            else:
                return {"message": content}
                
        except Exception as e:
            error_msg = f"Error in screening API call: {str(e)}"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current state of a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Current session data
        """
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {
            "session_id": session_id,
            "status": self.sessions[session_id].get("status", "unknown"),
            "conversation_length": len(self.sessions[session_id].get("conversation_history", [])),
            "has_diagnosis": "diagnosis_json" in self.sessions[session_id],
            "has_report": "report" in self.sessions[session_id],
            "recommended_assessment": self.sessions[session_id].get("recommended_assessment")
        }

class AssessmentAgent:
    """Temporary placeholder for AssessmentAgent class"""
    
    async def conduct_assessment(self, assessment_id: str, patient_info: Dict[str, Any], 
                                screening_result: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Placeholder method for conducting assessment"""
        return {
            "assessment_id": assessment_id,
            "questions": ["This is a placeholder question. The AssessmentAgent is not fully implemented."],
            "status": "initialized"
        }
    
    async def process_assessment_results(self, assessment_id: str, responses: List[int], 
                                        patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder method for processing assessment results"""
        return {
            "assessment_id": assessment_id,
            "scores": {"placeholder": 0},
            "interpretation": "This is a placeholder. The AssessmentAgent is not fully implemented."
        }

class ReportAgent:
    """Temporary placeholder for ReportAgent class"""
    
    async def generate_report(self, patient_info: Dict[str, Any], symptoms: List[str],
                             screening_result: Dict[str, Any], assessment_results: Dict[str, Any],
                             conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Placeholder method for generating reports"""
        return {
            "patient_info": patient_info,
            "summary": "This is a placeholder report. The ReportAgent is not fully implemented.",
            "recommendations": ["This is a placeholder recommendation."]
        } 