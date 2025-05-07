import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from pydantic import BaseModel

# Langchain Core Imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Langchain Community & Tool Imports
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

from routers.auth import get_current_user

# Set up OpenAI credentials
os.environ["OPENAI_API_KEY"] = "sk-UnNXXoNG6qqa1RUl24zKrakQaHBeyxqkxEtaVwGbSrGlRQxl"
os.environ["OPENAI_API_BASE"] = "https://xiaoai.plus/v1"

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

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
            print(f"Retrieved results: {results}")
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
        ("system", """Your Name is Dr. Mind, a professional mental disorder screening specialist. You will screen for mental disorders based on the patient's symptoms and return a JSON output of the disorder name and the probability of the diagnosis at the end of the conversation.

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
10. End the conversation with one JSON output only, remove all other text. : {{"result":["disorder name"], "probabilities":[0.X]}} (where X is a number between 0-9 representing how confident you are in the diagnosis).

     
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

    # Create agent and executor
    agent = create_openai_tools_agent(chat_model, [retriever_tool], prompt)
    agent_executor = AgentExecutor(agent=agent, tools=[retriever_tool], verbose=True)

except Exception as e:
    print(f"Initialization error: {e}\n{traceback.format_exc()}")
    raise

# Store chat histories
chat_histories: Dict[str, List[Any]] = {}

@router.post("/start")
async def start_chat(current_user: dict = Depends(get_current_user)):
    """Start a new chat session with a greeting message."""
    user_id = str(current_user["id"])
    user_name = f"{current_user['first_name']} {current_user['last_name']}"
    
    # Initialize chat history
    chat_histories[user_id] = []
    
    # Generate greeting message
    greeting = f"Hello {user_name}, I'm Dr. Mind. I'm here to help assess your mental health concerns. How are you feeling recently?"
    
    # Add greeting to history
    chat_histories[user_id].append(AIMessage(content=greeting))
    
    return {
        "message": greeting
    }

@router.post("/message")
async def chat_message(
    chat_message: ChatMessage,
    current_user: dict = Depends(get_current_user)):
    """Process a chat message using the agent."""
    user_id = str(current_user["id"])
    
    # Initialize chat history if it doesn't exist
    if user_id not in chat_histories:
        await start_chat(current_user)
    
    try:
        # Add user message to history
        chat_histories[user_id].append(HumanMessage(content=chat_message.message))
        
        # Get response from agent
        response = await agent_executor.ainvoke({
            "input": chat_message.message,
            "chat_history": chat_histories[user_id]
        })
        
        # Add agent response to history
        ai_message = AIMessage(content=response["output"])
        chat_histories[user_id].append(ai_message)
        
        return {
            "message": response["output"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        ) 