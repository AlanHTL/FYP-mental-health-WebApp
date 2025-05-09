import os
import traceback
import json
import re
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import httpx

# Langchain Core Imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import PydanticOutputParser

# Langchain Community & Tool Imports
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

from routers.auth import get_current_user
from models import DiagnosisReport
from database import diagnosis_reports_collection

# Set up OpenAI credentials
os.environ["OPENAI_API_KEY"] = os.getenv("API_KEY")
os.environ["OPENAI_API_BASE"] = os.getenv("API_BASE")

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

class AssessmentOption(BaseModel):
    option_id: str

# Assessment data
DASS21_QUESTIONS = [
    "I found it hard to wind down",
    "I was aware of dryness of my mouth",
    "I couldn't seem to experience any positive feeling at all",
    "I experienced breathing difficulty (e.g., excessively rapid breathing, breathlessness in the absence of physical exertion)",
    "I found it difficult to work up the initiative to do things",
    "I tended to over-react to situations",
    "I experienced trembling (e.g., in the hands)",
    "I felt that I was using a lot of nervous energy",
    "I was worried about situations in which I might panic and make a fool of myself",
    "I felt that I had nothing to look forward to",
    "I found myself getting agitated",
    "I found it difficult to relax",
    "I felt down-hearted and blue",
    "I was intolerant of anything that kept me from getting on with what I was doing",
    "I felt I was close to panic",
    "I was unable to become enthusiastic about anything",
    "I felt I wasn't worth much as a person",
    "I felt that I was rather touchy",
    "I was aware of the action of my heart in the absence of physical exertion (e.g. sense of heart rate increase, heart missing a beat)",
    "I felt scared without any good reason",
    "I felt that life was meaningless"
]

DASS21_OPTIONS = [
    {"id": "0", "text": "Did not apply to me at all"},
    {"id": "1", "text": "Applied to me to some degree, or some of the time"},
    {"id": "2", "text": "Applied to me to a considerable degree, or a good part of time"},
    {"id": "3", "text": "Applied to me very much, or most of the time"}
]

PCL5_QUESTIONS = [
    "Repeated, disturbing, and unwanted memories of the stressful experience?",
    "Repeated, disturbing dreams of the stressful experience?",
    "Suddenly feeling or acting as if the stressful experience were actually happening again (as if you were actually back there reliving it)?",
    "Feeling very upset when something reminded you of the stressful experience?",
    "Having strong physical reactions when something reminded you of the stressful experience (for example, heart pounding, trouble breathing, sweating)?",
    "Avoiding memories, thoughts, or feelings related to the stressful experience?",
    "Avoiding external reminders of the stressful experience (for example, people, places, conversations, activities, objects, or situations)?",
    "Trouble remembering important parts of the stressful experience?",
    "Having strong negative beliefs about yourself, other people, or the world (for example, having thoughts such as: I am bad, there is something seriously wrong with me, no one can be trusted, the world is completely dangerous)?",
    "Blaming yourself or someone else for the stressful experience or what happened after it?",
    "Having strong negative feelings such as fear, horror, anger, guilt, or shame?",
    "Loss of interest in activities that you used to enjoy?",
    "Feeling distant or cut off from other people?",
    "Trouble experiencing positive feelings (for example, being unable to feel happiness or have loving feelings for people close to you)?",
    "Irritable behavior, angry outbursts, or acting aggressively?",
    "Taking too many risks or doing things that could cause you harm?",
    "Being \"superalert\" or watchful or on guard?",
    "Feeling jumpy or easily startled?",
    "Having difficulty concentrating?",
    "Trouble falling or staying asleep?"
]

PCL5_OPTIONS = [
    {"id": "0", "text": "Not at all"},
    {"id": "1", "text": "A little bit"},
    {"id": "2", "text": "Moderately"},
    {"id": "3", "text": "Quite a bit"},
    {"id": "4", "text": "Extremely"}
]

# Get the absolute path to the FAISS index directory
current_dir = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(current_dir, "faiss_index")
print(f"FAISS index path: {FAISS_INDEX_PATH}")

# Initialize components
chat_model = None
embeddings_model = None
vector_store = None
retriever_tool = None
agent_executor = None

try:
    # Initialize chat model
    chat_model = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        base_url=os.environ["OPENAI_API_BASE"],
        api_key=os.environ["OPENAI_API_KEY"]
    )

    # Initialize embeddings model
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        base_url=os.environ["OPENAI_API_BASE"],
        api_key=os.environ["OPENAI_API_KEY"]
    )

    # Load FAISS index
    try:
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings_model,
            allow_dangerous_deserialization=True
        )
        print("FAISS index loaded successfully.")
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        print("Creating sample vector store...")
        
        # Sample mental disorder descriptions
        sample_texts = [
            """{"name": "Major Depressive Disorder", "criteria": "A. Five (or more) of the following symptoms have been present during the same 2-week period and represent a change from previous functioning; at least one of the symptoms is either (1) depressed mood or (2) loss of interest or pleasure: 1. Depressed mood most of the day, nearly every day. 2. Markedly diminished interest or pleasure in all, or almost all, activities most of the day, nearly every day. 3. Significant weight loss when not dieting or weight gain, or decrease or increase in appetite nearly every day. 4. Insomnia or hypersomnia nearly every day. 5. Psychomotor agitation or retardation nearly every day. 6. Fatigue or loss of energy nearly every day. 7. Feelings of worthlessness or excessive or inappropriate guilt nearly every day. 8. Diminished ability to think or concentrate, or indecisiveness, nearly every day. 9. Recurrent thoughts of death, recurrent suicidal ideation without a specific plan, or a suicide attempt or a specific plan for committing suicide."}""",
            
            """{"name": "Generalized Anxiety Disorder", "criteria": "A. Excessive anxiety and worry (apprehensive expectation), occurring more days than not for at least 6 months, about a number of events or activities (such as work or school performance). B. The individual finds it difficult to control the worry. C. The anxiety and worry are associated with three (or more) of the following six symptoms (with at least some symptoms having been present for more days than not for the past 6 months): 1. Restlessness or feeling keyed up or on edge. 2. Being easily fatigued. 3. Difficulty concentrating or mind going blank. 4. Irritability. 5. Muscle tension. 6. Sleep disturbance (difficulty falling or staying asleep, or restless, unsatisfying sleep)."}""",
            
            """{"name": "Normal", "criteria": "The individual does not meet criteria for any mental disorder. Normal responses to stressors may include temporary anxiety, sadness, or stress that does not significantly impair daily functioning and resolves naturally. Common experiences include: 1. Temporary nervousness before events like exams or presentations. 2. Brief periods of sadness following disappointments. 3. Short-term sleep changes during stressful periods. 4. Appropriate emotional responses to life circumstances."}"""
        ]
        
        # Create documents from sample texts
        sample_docs = [Document(page_content=text) for text in sample_texts]
        
        # Create vector store from documents
        vector_store = FAISS.from_documents(sample_docs, embeddings_model)
        
        # Save the vector store
        os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
        vector_store.save_local(FAISS_INDEX_PATH)
        print("Sample vector store created and saved successfully.")

    # Create retriever tool
    def search_criteria(query: str) -> str:
        """Search the diagnostic criteria database."""
        try:
            docs = vector_store.similarity_search(query, k=3)
            results = "\n".join([doc.page_content for doc in docs])
            
            # Get the current user's ID from the request context
            # Note: This requires modifying the function signature to accept user_id
            if hasattr(search_criteria, 'current_user_id'):
                user_id = search_criteria.current_user_id
                if user_id in internal_chat_histories:
                    # Add retrieval results to internal chat history
                    internal_chat_histories[user_id].append(
                        AIMessage(content=f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>")
                    )
            
            return f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>"
        except Exception as e:
            return f"Error retrieving information: {str(e)}"

    retriever_tool = Tool(
        name="search_document_database",
        description="Searches and returns relevant diagnostic criteria based on symptoms.",
        func=search_criteria,
    )

    # Create agent prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Your Name is Dr. Mind, a professional mental disorder screening specialist. You will screen for mental disorders based on the patient's symptoms through asking questions.

step by step process:
1. Ask about their feelings, why they feel this way, physical symptoms, and the duration of these symptoms.
2. After collecting initial information, use the search_document_database tool to query the mental disorders database with specific symptoms described.
3. Analyze if the patient's symptoms fulfill the diagnostic criteria based on the retrieved information in the chat history.
4. Ask follow-up questions if more information is needed to confirm or classify the disorder based on the retrieved information.
5. Check chat history, if the retrieved information is already in the chat history, do not use the tool again, just use the retrieved information to make a diagnosis, because the retrieved tools is very costly.
6. If the criteria are fulfilled or most of the main criteria are met, go to point 8. and output the diagnosis in JSON format.
7. If symptoms don't match the any disorder of the retrieved result in chat history, you can create a new query search again.
8. When you think that you find a diagnosis, output the result in JSON format only, Do not conclude any other text, just output the result. example: Dr. Mind: {{"result":["disorder name"], "probabilities":[0.X]}} (where X is a number between 0-9 representing how confident you are in the diagnosis).

*Make sure the output to patient follow the Output Guidelines strictly, check the guidelines every time you generate the output. If the output not follow the guidelines, fix it*
*Output Guidelines:*
- Think step by step and explain your reasoning.
- Do not show your thinking in the conversation, remove all the text for the thinking.
- You are not allowed to tell the patient about your thinking of classification, just ask questions and make a diagnosis using Json format output.
- Do not tell the patient about the retrieved information, for example, do not say "Based on the information retrieved from the database, the patient is likely to have [diagnosis]".
- Just focus on asking questions for the classification of the disorder.
- The retrieved information is only for the classification of the disorder, do not tell the patient anything about the retrieved information.
- Use the tool to search once only, if the chat history already have the retrieved information, do not use the tool again, unless the symptoms don't match the any disorder of the retrieved result in chat history 
- Be compassionate and professional in your communication.
- Ask one question at a time to avoid overwhelming the patient.
- Provide examples answers of the questions you are asking.
- Before making a diagnosis, verify that the patient meets the required criteria.
- You are not allowed to make any diagnosis prediction about the disorder using sentence, like "Based on your symptoms, it seems to align with [diagnosis]" or "it might be [diagnosis]", just focus on asking questions for getting more information. If the patient recived a diagnosis in normal sentence, the patient will feel confused and the diagnosis will not be accurate.
- Once you think that you find a diagnosis, output the result in JSON format.
- For the JSON output, check if there are any text in front of the JSON or after the JSON in the response, if there are, remove them.
- The patient could be normal, please think step by step before making a diagnosis, normal diagnosis is "result": ["Normal"]
- For emergency situations or suicidal actions, provide immediate help information: full_text("*I understand you may be going through a difficult time right now. Your safety and wellbeing are the top priority. Please know that help is available 24/7:\n\n1. If you are in immediate danger:\n- Move to a safe location if possible\n- Call emergency services: 999\n- Stay on the line with the operator\n\n2. 24/7 Crisis Support Hotlines:\n- 明愛向晴軒 (Family Crisis Line): 18288\n- 醫院管理局 (Mental Health Line): 2466 7350\n- 生命熱線 (Suicide Prevention): 2382 0000\n- 香港撒瑪利亞防止自殺會: 2389 2222\n- 撒瑪利亞會 (Multilingual): 2896 0000\n\n3. Additional Support:\n- Visit your nearest A&E department\n- Contact your regular healthcare provider\n- Social Welfare Department: 2343 2255\n\nRemember, seeking help is a sign of strength. You don't have to go through this alone.\n\nFirst, I need to know - are you currently in a safe place? If not, please use the emergency contacts above immediately.\n\nWould you like to continue with our conversation when you feel ready?*")


Here are examples of how Dr Mind use tools and think step by step: {{patient: [patient's symptoms]}}, {{tool: [search_document_database]}}, {{think: [Dr. Mind's thought process]}}, {{Dr. Mind: [Dr. Mind's response]}}
Example 1:
Patient: I've been feeling really down for the past few months, can't sleep, and lost interest in everything.
Think: i need more information to make a diagnosis
Dr. Mind: Let me ask you a few questions to understand better. Have you been feeling sad or empty most of the day?
Patient: Yes, almost every day.
Tools: search_document_database
Think: based on the retrieved information, the patient is likely to have Major Depressive Disorder, but i need more information to confirm the diagnosis
Dr. Mind: Have you lost interest in activities you used to enjoy?
Patient: Yes, I don't enjoy anything anymore.
Think: based on the retrieved information, the patient is likely to have Major Depressive Disorder, but i need more information to confirm the diagnosis
Dr. Mind: How has your sleep been?
Patient: I can't sleep at night, but I sleep too much during the day.
Think: based on the retrieved information, the patient is likely to have Major Depressive Disorder, but i need more information to confirm the diagnosis
Dr. Mind: Have you had any thoughts about death or suicide?
Patient: Yes, sometimes I think about it.
Think: Based on the symptoms you've described, it seems that you may meet the criteria for Major Depressive Disorder.
Dr. Mind: {{"result":["Major Depressive Disorder"], "probabilities":[0.8]}}

"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Create agent and executor
    agent = create_openai_tools_agent(chat_model, [retriever_tool], prompt)
    agent_executor = AgentExecutor(agent=agent, tools=[retriever_tool], verbose=True)

except Exception as e:
    print(f"Initialization error: {e}\n{traceback.format_exc()}")
    raise

# Store chat histories
chat_histories: Dict[str, List[Any]] = {}
internal_chat_histories: Dict[str, List[Any]] = {}  # New dictionary for internal history

# Store user assessment states
user_assessment_states: Dict[str, Dict[str, Any]] = {}

def is_diagnosis_result(message: str) -> Optional[Dict]:
    """Check if the message is a diagnosis result in JSON format."""
    try:
        # Look for JSON pattern in the message
        json_match = re.search(r'({(?:"result":|\'result\':).*})', message)
        if json_match:
            json_str = json_match.group(1)
            # Parse the JSON
            result = json.loads(json_str)
            if 'result' in result and 'probabilities' in result:
                return result
        return None
    except:
        return None

def get_assessment_type(diagnosis: List[str]) -> Optional[str]:
    """Determine which assessment to use based on diagnosis."""
    depression_anxiety_disorders = [
        "Major Depressive Disorder", 
        "Persistent Depressive Disorder",
        "Generalized Anxiety Disorder", 
        "Panic Disorder"
    ]
    
    ptsd_disorders = ["Posttraumatic Stress Disorder"]
    
    for disorder in diagnosis:
        if any(d.lower() in disorder.lower() for d in depression_anxiety_disorders):
            return "DASS21"
        elif any(d.lower() in disorder.lower() for d in ptsd_disorders):
            return "PCL5"
    
    return None

def get_assessment_question(assessment_type: str, question_index: int) -> Dict:
    """Get assessment question and options based on type and index."""
    if assessment_type == "DASS21":
        if question_index < len(DASS21_QUESTIONS):
            return {
                "question": f"Question {question_index + 1}/{len(DASS21_QUESTIONS)}: {DASS21_QUESTIONS[question_index]}",
                "options": DASS21_OPTIONS
            }
        return {"question": "Assessment completed", "options": []}
    
    elif assessment_type == "PCL5":
        if question_index < len(PCL5_QUESTIONS):
            return {
                "question": f"Question {question_index + 1}/{len(PCL5_QUESTIONS)}: {PCL5_QUESTIONS[question_index]}",
                "options": PCL5_OPTIONS
            }
        return {"question": "Assessment completed", "options": []}
    
    return {"question": "No assessment needed", "options": []}

def calculate_dass21_scores(answers: List[int]) -> Dict:
    """Calculate DASS-21 scores for stress, anxiety, and depression."""
    # Stress: Questions 1, 6, 8, 11, 12, 14, 18 (indices 0, 5, 7, 10, 11, 13, 17)
    stress = sum([answers[i] for i in [0, 5, 7, 10, 11, 13, 17]]) * 2
    
    # Anxiety: Questions 2, 4, 7, 9, 15, 19, 20 (indices 1, 3, 6, 8, 14, 18, 19)
    anxiety = sum([answers[i] for i in [1, 3, 6, 8, 14, 18, 19]]) * 2
    
    # Depression: Questions 3, 5, 10, 13, 16, 17, 21 (indices 2, 4, 9, 12, 15, 16, 20)
    depression = sum([answers[i] for i in [2, 4, 9, 12, 15, 16, 20]]) * 2
    
    # Determine severity levels
    stress_level = "Normal"
    if stress >= 34:
        stress_level = "Extremely Severe"
    elif stress >= 26:
        stress_level = "Severe"
    elif stress >= 19:
        stress_level = "Moderate"
    elif stress >= 15:
        stress_level = "Mild"
    
    anxiety_level = "Normal"
    if anxiety >= 20:
        anxiety_level = "Extremely Severe"
    elif anxiety >= 15:
        anxiety_level = "Severe"
    elif anxiety >= 10:
        anxiety_level = "Moderate"
    elif anxiety >= 8:
        anxiety_level = "Mild"
    
    depression_level = "Normal"
    if depression >= 28:
        depression_level = "Extremely Severe"
    elif depression >= 21:
        depression_level = "Severe"
    elif depression >= 14:
        depression_level = "Moderate"
    elif depression >= 10:
        depression_level = "Mild"
    
    return {
        "stress": {
            "score": stress,
            "level": stress_level
        },
        "anxiety": {
            "score": anxiety,
            "level": anxiety_level
        },
        "depression": {
            "score": depression,
            "level": depression_level
        }
    }

def calculate_pcl5_score(answers: List[int]) -> Dict:
    """Calculate PCL-5 score for PTSD."""
    total_score = sum(answers)
    
    # Determine severity based on total score
    severity = "None"
    if total_score >= 33:
        severity = "Probable PTSD"
    elif total_score >= 15:
        severity = "Some PTSD symptoms"
    
    return {
        "total_score": total_score,
        "severity": severity
    }

@router.post("/start")
async def start_chat(current_user: dict = Depends(get_current_user)):
    """Start a new chat session with a greeting message."""
    user_id = str(current_user["id"])
    user_name = f"{current_user['first_name']} {current_user['last_name']}"
    
    # Initialize both chat histories
    chat_histories[user_id] = []
    internal_chat_histories[user_id] = []
    
    # Initialize assessment state
    user_assessment_states[user_id] = {
        "in_assessment": False,
        "assessment_type": None,
        "question_index": 0,
        "answers": [],
        "diagnosis": None,
        "completed": False
    }
    
    # Generate greeting message
    greeting = f"Hello {user_name}, I'm Dr. Mind. I'm here to help assess your mental health concerns. How are you feeling recently?"
    
    # Add greeting to both histories
    chat_histories[user_id].append(AIMessage(content=greeting))
    internal_chat_histories[user_id].append(AIMessage(content=greeting))
    
    return {
        "message": greeting
    }

@router.post("/message")
async def chat_message(
    chat_message: ChatMessage,
    current_user: dict = Depends(get_current_user)):
    """Process a chat message using the agent."""
    user_id = str(current_user["id"])
    
    # Initialize chat histories if they don't exist
    if user_id not in chat_histories or user_id not in internal_chat_histories:
        await start_chat(current_user)
    
    # Get assessment state
    assessment_state = user_assessment_states.get(user_id, {
        "in_assessment": False,
        "assessment_type": None,
        "question_index": 0,
        "answers": [],
        "diagnosis": None,
        "completed": False
    })
    
    try:
        # Check if we're in an assessment
        if assessment_state["in_assessment"]:
            # Add user message to both histories
            chat_histories[user_id].append(HumanMessage(content=chat_message.message))
            internal_chat_histories[user_id].append(HumanMessage(content=chat_message.message))
            
            try:
                # Parse user's answer (should be a number corresponding to option)
                answer = int(chat_message.message)
                assessment_state["answers"].append(answer)
                
                # Move to next question
                assessment_state["question_index"] += 1
                
                # Check if assessment is complete
                if (assessment_state["assessment_type"] == "DASS21" and assessment_state["question_index"] >= len(DASS21_QUESTIONS)) or \
                   (assessment_state["assessment_type"] == "PCL5" and assessment_state["question_index"] >= len(PCL5_QUESTIONS)):
                    
                    # Calculate results
                    if assessment_state["assessment_type"] == "DASS21":
                        results = calculate_dass21_scores(assessment_state["answers"])
                        result_message = f"""
DASS-21 Assessment Results:

Depression: {results['depression']['score']} - {results['depression']['level']}
Anxiety: {results['anxiety']['score']} - {results['anxiety']['level']}
Stress: {results['stress']['score']} - {results['stress']['level']}

Thank you for completing the assessment. Would you like to generate a diagnosis report?
                        """
                    else:  # PCL5
                        results = calculate_pcl5_score(assessment_state["answers"])
                        result_message = f"""
PCL-5 Assessment Results:

Total Score: {results['total_score']}
Severity: {results['severity']}

Thank you for completing the assessment. Would you like to generate a diagnosis report?
                        """
                    
                    # Add assessment results to chat history
                    chat_histories[user_id].append(AIMessage(content=result_message))
                    internal_chat_histories[user_id].append(AIMessage(content=f"Assessment results: {json.dumps(results)}"))
                    
                    # End assessment
                    assessment_state["in_assessment"] = False
                    assessment_state["completed"] = True
                    user_assessment_states[user_id] = assessment_state
                    
                    return {
                        "message": result_message,
                        "show_report_button": True
                    }
                
                # Get next question
                question_data = get_assessment_question(
                    assessment_state["assessment_type"], 
                    assessment_state["question_index"]
                )
                
                # Save state
                user_assessment_states[user_id] = assessment_state
                
                # Add question to chat history
                response_message = question_data["question"]
                chat_histories[user_id].append(AIMessage(content=response_message))
                internal_chat_histories[user_id].append(AIMessage(content=response_message))
                
                return {
                    "message": response_message,
                    "assessment": True,
                    "options": question_data["options"]
                }
            
            except ValueError:
                # Invalid answer format
                error_message = "Please select one of the provided options by entering the corresponding number."
                chat_histories[user_id].append(AIMessage(content=error_message))
                internal_chat_histories[user_id].append(AIMessage(content=error_message))
                
                # Re-send the current question
                question_data = get_assessment_question(
                    assessment_state["assessment_type"], 
                    assessment_state["question_index"]
                )
                
                return {
                    "message": error_message,
                    "assessment": True,
                    "options": question_data["options"]
                }
                
        # Regular chat flow (not in assessment)
        # Set current user ID for the search function
        search_criteria.current_user_id = user_id
        
        # Add user message to both histories
        chat_histories[user_id].append(HumanMessage(content=chat_message.message))
        internal_chat_histories[user_id].append(HumanMessage(content=chat_message.message))
        
        # Check for report generation command
        if chat_message.message.lower() in ["generate report", "generate diagnosis report"]:
            # Generate a diagnosis report
            report = await generate_diagnosis_report(user_id, current_user)
            
            # Add report to chat history
            chat_histories[user_id].append(AIMessage(content=report))
            internal_chat_histories[user_id].append(AIMessage(content=report))
            
            return {
                "message": report
            }
        
        # Get response from agent using internal history
        response = await agent_executor.ainvoke({
            "input": chat_message.message,
            "chat_history": internal_chat_histories[user_id]
        })
        
        # Process the response
        response_content = response["output"]
        
        # Check if the response is a diagnosis result
        diagnosis_result = is_diagnosis_result(response_content)
        if diagnosis_result:
            # Store the diagnosis
            assessment_state["diagnosis"] = diagnosis_result["result"]
            
            # Check if we need to start an assessment
            assessment_type = get_assessment_type(diagnosis_result["result"])
            if assessment_type:
                # Start assessment
                assessment_state["in_assessment"] = True
                assessment_state["assessment_type"] = assessment_type
                assessment_state["question_index"] = 0
                assessment_state["answers"] = []
                
                # Save state
                user_assessment_states[user_id] = assessment_state
                
                # Add diagnosis to chat history
                chat_histories[user_id].append(AIMessage(content=response_content))
                internal_chat_histories[user_id].append(AIMessage(content=response_content))
                
                # Get first assessment question
                question_data = get_assessment_question(assessment_type, 0)
                
                # Add assessment introduction and question to chat history
                assessment_intro = f"""
Based on your responses, I'd like to proceed with a standardized assessment to gain more detailed insights.

I'll be asking you several questions from the {assessment_type} assessment. Please select the option that best describes your experience. The questions are as follows: \n


{question_data["question"]}
                """
                
                chat_histories[user_id].append(AIMessage(content=assessment_intro))
                internal_chat_histories[user_id].append(AIMessage(content=assessment_intro))
                
                return {
                    "message": assessment_intro,
                    "assessment": True,
                    "options": question_data["options"]
                }
            else:
                # No assessment needed, just add diagnosis to chat history
                chat_histories[user_id].append(AIMessage(content=response_content))
                internal_chat_histories[user_id].append(AIMessage(content=response_content))
                
                # Indicate assessment is completed (skipped)
                assessment_state["completed"] = True
                user_assessment_states[user_id] = assessment_state
                
                # Offer to generate a report
                report_offer = "Would you like to generate a diagnosis report?"
                chat_histories[user_id].append(AIMessage(content=report_offer))
                internal_chat_histories[user_id].append(AIMessage(content=report_offer))
                
                return {
                    "message": response_content,
                    "diagnosis": True,
                    "follow_up": report_offer,
                    "show_report_button": True
                }
        
        # Add response to both histories
        chat_histories[user_id].append(AIMessage(content=response_content))
        internal_chat_histories[user_id].append(AIMessage(content=response_content))
        print(internal_chat_histories[user_id])
        
        # Clear the current user ID
        search_criteria.current_user_id = None
        
        return {
            "message": response_content
        }
        
    except Exception as e:
        # Clear the current user ID in case of error
        search_criteria.current_user_id = None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

# Define the response schema for the report
class DiagnosisReportSchema(BaseModel):
    diagnosis: str = Field(description="The diagnosis result, which is the disorder name")
    details: str = Field(description="Detailed information about the patient's experience, feelings, assessment results, and other diagnostic details (100-200 words)")
    symptoms: List[str] = Field(description="List of reported symptoms and observations")
    recommendations: List[str] = Field(description="List of recommended actions and treatments")
    llm_analysis: Dict[str, Any] = Field(description="Additional analysis and insights from the LLM")

# Create the parser
parser = PydanticOutputParser(pydantic_object=DiagnosisReportSchema)

# Create the format instructions
format_instructions = parser.get_format_instructions()

# Create the prompt template
REPORT_TEMPLATE = """You are a mental health professional tasked with generating a comprehensive diagnosis report.

Based on the following information:
Disorder result: {diagnosis}
Assessment results: {assessment_results}
Chat history: {chat_history}

Generate a structured diagnosis report that includes:
1. The diagnosis result - a concise statement of the diagnosis
2. A detailed narrative (details field) describing the patient's experiences, feelings, assessment results, duration of symptoms, and other relevant information about their condition (100-200 words)
3. A comprehensive list of symptoms and observations
4. Specific recommendations for treatment and next steps
5. Additional analysis and insights

{format_instructions}

Remember to be professional, compassionate, and thorough in your analysis."""

report_prompt = ChatPromptTemplate.from_template(REPORT_TEMPLATE)

# Create the chain
report_chain = report_prompt | chat_model | parser

async def generate_diagnosis_report(user_id: str, current_user: dict) -> str:
    """Generate a diagnosis report based on chat history and assessment results."""
    try:
        print(f"DEBUG: Generating diagnosis report for user ID: {user_id}")
        
        # Get assessment state
        assessment_state = user_assessment_states.get(user_id, {})
        
        # Create a summary of the diagnosis and assessment results
        diagnosis = assessment_state.get("diagnosis", ["Unknown"])
        print(f"DEBUG: Diagnosis from assessment: {diagnosis}")
        
        # Extract assessment results from chat history
        assessment_results = None
        for message in internal_chat_histories[user_id]:
            if isinstance(message, AIMessage) and message.content.startswith("Assessment results:"):
                try:
                    assessment_results = json.loads(message.content.replace("Assessment results:", "").strip())
                    print(f"DEBUG: Found assessment results: {assessment_results}")
                except Exception as e:
                    print(f"ERROR: Failed to parse assessment results: {str(e)}")
        
        if not assessment_results:
            print("DEBUG: No assessment results found")
        
        # Generate structured report using the chain
        print("DEBUG: Generating structured report using LangChain")
        report_data = await report_chain.ainvoke({
            "diagnosis": diagnosis,
            "assessment_results": assessment_results,
            "chat_history": internal_chat_histories[user_id],
            "format_instructions": format_instructions
        })
        
        print(f"DEBUG: Report data generated with diagnosis: {report_data.diagnosis}")
        print(f"DEBUG: Report details: {report_data.details}")
        print(f"DEBUG: Report symptoms: {report_data.symptoms}")
        print(f"DEBUG: Report recommendations: {report_data.recommendations}")
        
        # Create diagnosis report directly using the collection
        diagnosis_report = {
            "id": str(datetime.utcnow().timestamp()),
            "patient_id": current_user["id"],
            "diagnosis": report_data.diagnosis,
            "details": report_data.details,
            "symptoms": report_data.symptoms,
            "recommendations": report_data.recommendations,
            "created_at": datetime.utcnow(),
            "is_physical": False,  # AI-generated reports are marked as non-physical
            "llm_analysis": report_data.llm_analysis
        }
        
        print(f"DEBUG: Saving diagnosis report to database with ID: {diagnosis_report['id']}")
        
        try:
            # Save to database
            await diagnosis_reports_collection.insert_one(diagnosis_report)
            print("DEBUG: Diagnosis report saved successfully")
        except Exception as e:
            print(f"ERROR: Failed to save diagnosis report to database: {str(e)}")
            raise
        
        # Format the report for display
        print("DEBUG: Formatting report for display")
        formatted_report = f"""
# Mental Health Diagnosis Report

## Diagnosis
{report_data.diagnosis}

## Details
{report_data.details}

## Symptoms
{chr(10).join(f"- {symptom}" for symptom in report_data.symptoms)}

## Recommendations
{chr(10).join(f"- {recommendation}" for recommendation in report_data.recommendations)}

## Additional Analysis
{json.dumps(report_data.llm_analysis, indent=2)}

*This report has been generated based on your interaction with Dr. Mind and has been saved to your records. Please review it in the View Reports page.*
"""
        
        return formatted_report
    
    except Exception as e:
        error_msg = f"Error generating report: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        return f"Error generating report: {str(e)}"

@router.post("/report")
async def generate_report(current_user: dict = Depends(get_current_user)):
    """Generate a diagnosis report for the user."""
    user_id = str(current_user["id"])
    
    if user_id not in internal_chat_histories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chat history found. Please start a conversation first."
        )
    
    # Generate report
    report = await generate_diagnosis_report(user_id, current_user)
    
    # Add report to chat history
    chat_histories[user_id].append(AIMessage(content=report))
    internal_chat_histories[user_id].append(AIMessage(content=report))
    
    return {
        "message": "Report has been generated and saved. You can view it in the View Reports page.",
        "report": report
    } 