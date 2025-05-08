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
        temperature=0.6,
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
- Do not tell the patient about the retrieved information, for example, do not say "Based on the information retrieved from the database, the patient is likely to have [diagnosis]".
- Just focus on asking questions for the classification of the disorder.
- The retrieved information is only for the classification of the disorder, do not tell the patient anything about the retrieved information.
- Use the tool to search once only, if the chat history already have the retrieved information, do not use the tool again, unless the symptoms don't match the any disorder of the retrieved result in chat history 
- Be compassionate and professional in your communication.
- Ask one question at a time to avoid overwhelming the patient.
- Provide examples answers of the questions you are asking.
- Before making a diagnosis, verify that the patient meets the required criteria.
- Do not make any prediction about the disorder, like "it seems to align with [diagnosis]" or "it might be [diagnosis]", just focus on asking questions for getting more information.
- Once you think that you find a diagnosis, output the result in JSON format.
- For the JSON output, check if there are any text in front of the JSON or after the JSON in the response, if there are, remove them.
- The patient could be normal, please think step by step before making a diagnosis, normal diagnosis is "result": ["Normal"]
- For emergency situations or suicidal actions, provide immediate help information: full_text("*\n1. *If you are in an immediately dangerous situation (such as on a rooftop, bridge, or with means of harm):\n- Move to a safe location immediately\n- Call emergency services: 999\n- Stay on the line with emergency services\n\n2. **For immediate support:\n- Go to your nearest emergency room/A&E department\n- Call The Samaritans hotline (Multilingual): (852) 2896 0000\n- Call Suicide Prevention Service hotline (Cantonese): (852) 2382 0000\n\nAre you currently in a safe location?* If not, please seek immediate help using the emergency contacts above.\n*** Do you want to keep going with the screening?")


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

@router.post("/start")
async def start_chat(current_user: dict = Depends(get_current_user)):
    """Start a new chat session with a greeting message."""
    user_id = str(current_user["id"])
    user_name = f"{current_user['first_name']} {current_user['last_name']}"
    
    # Initialize both chat histories
    chat_histories[user_id] = []
    internal_chat_histories[user_id] = []
    
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
    
    try:
        # Set current user ID for the search function
        search_criteria.current_user_id = user_id
        
        # Add user message to both histories
        chat_histories[user_id].append(HumanMessage(content=chat_message.message))
        internal_chat_histories[user_id].append(HumanMessage(content=chat_message.message))
        
        # Get response from agent using internal history
        response = await agent_executor.ainvoke({
            "input": chat_message.message,
            "chat_history": internal_chat_histories[user_id]
        })
        
        # Process the response
        response_content = response["output"]
        
        # Add clean response to user-facing history
        chat_histories[user_id].append(AIMessage(content=response_content))
        
        # Add response to internal history
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