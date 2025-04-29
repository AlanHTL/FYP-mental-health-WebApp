import os
import asyncio
import json
from aiohttp import web
import traceback 
import uuid # Needed if generating IDs on server side, but client sends it now
import sys
from pathlib import Path

# Langchain Core Imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

# Langchain OpenAI Imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Langchain Community & Tool Imports
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool # Import Tool for manual creation

# --- Environment Setup & Configuration ---
os.environ["OPENAI_API_KEY"] = "key"
os.environ["OPENAI_API_BASE"] = "base url"

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

# --- Langchain Chat Model Initialization ---
chat_model = None
try:
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        raise ValueError("OPENAI_API_KEY is missing or empty.")
    chat_model = ChatOpenAI(
        model="gpt-3.5-turbo", 
        temperature=0.7
    )
    print("ChatOpenAI model initialized successfully.")
except Exception as e:
    print(f"Error initializing ChatOpenAI model: {e}")
    chat_model = None

# --- RAG Setup (FAISS Index Loading and Retriever Tool) ---
embeddings_model = None
retriever_tool = None
vector_store = None # Define vector_store outside try block

try:
    # Langchain Core Imports
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.runnables.history import RunnableWithMessageHistory

    # Langchain Community & Tool Imports  
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain.tools import Tool
    
    # Try both imports to handle different versions
    try:
        from langchain_community.vectorstores import FAISS
        print("Using langchain_community.vectorstores.FAISS")
    except ImportError:
        from langchain.vectorstores import FAISS
        print("Using langchain.vectorstores.FAISS")
        
    # --- Chat model initialization ---
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        raise ValueError("OPENAI_API_KEY is missing or empty.")
    chat_model = ChatOpenAI(
        model="gpt-3.5-turbo", 
        temperature=0.7
    )
    print("ChatOpenAI model initialized successfully.")
    
    # --- Embeddings model initialization ---
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-ada-002", 
        openai_api_base=os.environ.get("OPENAI_API_BASE")
    )
    print("OpenAIEmbeddings model initialized successfully.")
    
    # --- Load FAISS index (with various fallback approaches) ---
    # Attempt to load the index with detailed error handling
    try:
        print(f"Attempting to load FAISS index from: {FAISS_INDEX_PATH}")
        
        # First attempt: load without allow_dangerous_deserialization parameter
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH, 
            embeddings_model
        )
        print("FAISS index loaded successfully using standard load_local.")
    except Exception as e1:
        print(f"First FAISS loading attempt failed: {e1}")
        
        try:
            # Second attempt: try with newer API if available
            from langchain_community.vectorstores.faiss import FAISS as CommunityFAISS
            vector_store = CommunityFAISS.load_local(
                FAISS_INDEX_PATH,
                embeddings_model
            )
            print("FAISS index loaded successfully using community version.")
        except Exception as e2:
            print(f"Second FAISS loading attempt failed: {e2}")
            
            try:
                # Third attempt: load individual files manually
                import pickle
                import faiss
                
                # Load the index directly
                index = faiss.read_index(faiss_file)
                
                # Load the docstore and other data
                with open(pkl_file, "rb") as f:
                    pkl_data = pickle.load(f)
                
                # Manually create FAISS instance with appropriate parameters
                vector_store = FAISS(
                    embeddings_model, 
                    index, 
                    pkl_data["docstore"], 
                    pkl_data.get("index_to_docstore_id", {})
                )
                print("FAISS index loaded successfully using manual file loading.")
            except Exception as e3:
                print(f"Third FAISS loading attempt failed: {e3}")
                
                # Create a sample vector store with meaningful documents for testing
                from langchain.docstore.document import Document
                
                # Sample mental disorder descriptions to allow minimal testing
                sample_texts = [
                    """{"name": "Major Depressive Disorder", "criteria": "A. Five (or more) of the following symptoms have been present during the same 2-week period and represent a change from previous functioning; at least one of the symptoms is either (1) depressed mood or (2) loss of interest or pleasure: 1. Depressed mood most of the day, nearly every day. 2. Markedly diminished interest or pleasure in all, or almost all, activities most of the day, nearly every day. 3. Significant weight loss when not dieting or weight gain, or decrease or increase in appetite nearly every day. 4. Insomnia or hypersomnia nearly every day. 5. Psychomotor agitation or retardation nearly every day. 6. Fatigue or loss of energy nearly every day. 7. Feelings of worthlessness or excessive or inappropriate guilt nearly every day. 8. Diminished ability to think or concentrate, or indecisiveness, nearly every day. 9. Recurrent thoughts of death, recurrent suicidal ideation without a specific plan, or a suicide attempt or a specific plan for committing suicide."}""",
                    
                    """{"name": "Generalized Anxiety Disorder", "criteria": "A. Excessive anxiety and worry (apprehensive expectation), occurring more days than not for at least 6 months, about a number of events or activities (such as work or school performance). B. The individual finds it difficult to control the worry. C. The anxiety and worry are associated with three (or more) of the following six symptoms (with at least some symptoms having been present for more days than not for the past 6 months): 1. Restlessness or feeling keyed up or on edge. 2. Being easily fatigued. 3. Difficulty concentrating or mind going blank. 4. Irritability. 5. Muscle tension. 6. Sleep disturbance (difficulty falling or staying asleep, or restless, unsatisfying sleep)."}""",
                    
                    """{"name": "Normal", "criteria": "The individual does not meet criteria for any mental disorder. Normal responses to stressors may include temporary anxiety, sadness, or stress that does not significantly impair daily functioning and resolves naturally. Common experiences include: 1. Temporary nervousness before events like exams or presentations. 2. Brief periods of sadness following disappointments. 3. Short-term sleep changes during stressful periods. 4. Appropriate emotional responses to life circumstances."}"""
                ]
                
                sample_docs = [Document(page_content=text) for text in sample_texts]
                
                try:
                    from langchain_community.vectorstores import FAISS as DummyFAISS
                except ImportError:
                    from langchain.vectorstores import FAISS as DummyFAISS
                
                vector_store = DummyFAISS.from_documents(sample_docs, embeddings_model)
                print("Created sample vector store with basic mental disorder information since FAISS loading failed.")
                print(f"Original errors: {e1}\n{e2}\n{e3}")
    
    # --- Create the search tool ---
    def search_and_print(query: str) -> str:
        """Search the vector store, print status, and return formatted results."""
        print(f"DEBUG: Searching database with query: '{query}'")
        try:
            # Perform similarity search directly on the vector store
            docs = vector_store.similarity_search(query, k=3)  # Get top 3 results
            
            # For debugging, print each document content with clear separators
            print("DEBUG: RETRIEVAL RESULTS ----------------")
            for i, doc in enumerate(docs):
                print(f"DEBUG: RESULT {i+1}:")
                print(f"DEBUG: {doc.page_content}")
                print("DEBUG: -----------------------------------")
            
            # Format the results as a single string
            results = "\n".join([doc.page_content for doc in docs])
            return f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>"
        except Exception as e:
            print(f"Error during similarity search: {e}")
            return f"Error retrieving information: {str(e)}"
    
    # Create the tool using the direct search function
    retriever_tool = Tool(
        name="search_document_database",
        description="Searches and returns relevant information from the document database based on the user query.",
        func=search_and_print,
    )
    print("Retriever tool created successfully.")

except Exception as e:
    print(f"Error during initialization: {e}\n{traceback.format_exc()}")
    chat_model = None
    retriever_tool = None

# --- Agent Setup ---
# Define the prompt template for the agent
prompt = ChatPromptTemplate.from_messages([
    ("system", """Your Name is Dr. Mind, a professional mental disorder screening specialist. 

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
    MessagesPlaceholder(variable_name="agent_scratchpad") # For agent intermediate steps
])

agent = None
agent_executor = None
if chat_model and retriever_tool: # Only create agent if model and tool are ready
    tools = [retriever_tool]
    agent = create_openai_tools_agent(chat_model, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False) # Set verbose=True for debugging
    print("Agent Executor created successfully.")
else:
    print("Agent Executor could not be created because the chat model or retriever tool failed to initialize.")

# --- Conversation Memory Store ---
# Create a custom chat message history class that works with RunnableWithMessageHistory
class InMemoryChatMessageHistory(BaseChatMessageHistory):
    """Simple in-memory implementation of chat message history that meets requirements."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
    
    def add_message(self, message):
        """Add a message to the history."""
        self.messages.append(message)
        
    def clear(self):
        """Clear the message history."""
        self.messages = []

conversation_memory_store = {}

def get_memory(session_id: str):
    """Retrieves or creates memory for a session."""
    if session_id not in conversation_memory_store:
        # Each session gets its own memory instance
        conversation_memory_store[session_id] = InMemoryChatMessageHistory(session_id=session_id)
        print(f"Created new chat history for conversation_id: {session_id}")
    return conversation_memory_store[session_id]

# --- History-Aware Agent Executor ---
agent_with_history = None
if agent_executor:
    agent_with_history = RunnableWithMessageHistory(
        agent_executor,
        get_memory,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    print("Agent Executor wrapped with message history.")

# --- API Request Handler --- 
async def handle_chat(request):
    """Handles incoming chat requests using the agent executor with history."""
    if not agent_with_history:
        print("Error: Agent with history is not available.")
        # Provide a more specific error depending on what failed (model, tool, agent init)
        error_msg = "Chat agent initialization failed. Cannot process requests."
        if chat_model is None:
            error_msg = "Chat model failed to initialize."
        elif retriever_tool is None:
            error_msg = "Document retriever tool failed to initialize."
        return web.json_response({"error": error_msg}, status=500)

    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON format in request body"}, status=400)

        user_message = data.get("message")
        conversation_id = data.get("conversation_id")

        if not user_message or not isinstance(user_message, str):
            return web.json_response({"error": "Missing or invalid 'message' string in request body"}, status=400)
        if not conversation_id or not isinstance(conversation_id, str):
            return web.json_response({"error": "Missing or invalid 'conversation_id' string in request body"}, status=400)

        print(f"Processing message for conversation_id: {conversation_id}")
        
        # Check if this is a new conversation
        is_new_conversation = conversation_id not in conversation_memory_store
        
        # For new conversations, add the greeting to memory but don't return it
        if is_new_conversation:
            greeting = "Hi, I am Dr. Mind, a mental health screening specialist. May I have your name, please?"
            print(f"New conversation started. Adding greeting to memory: {greeting}")
            
            # Create the memory for this new conversation
            memory = get_memory(conversation_id)
            
            # Add the greeting as an AI message to the history
            memory.add_message(AIMessage(content=greeting))
            
            # Add the user's first message to history too
            memory.add_message(HumanMessage(content=user_message))
            
            # Continue with normal processing instead of returning the greeting
        
        # Configuration for the agent invocation, including the session ID for memory
        config = {"configurable": {"session_id": conversation_id}}
        
        # Use ainvoke for asynchronous execution
        print(f"Invoking agent for input: '{user_message[:50]}...' (ID: {conversation_id})")
        # The agent_with_history manages memory and tool calls
        response = await agent_with_history.ainvoke({"input": user_message}, config=config)
        print(f"Agent invocation successful for conversation_id: {conversation_id}")

        # Extract any retrieval results for debugging
        reply = response.get("output", "")
        
        # Log the raw response for debugging
        print(f"DEBUG: Raw agent response: {response}")

        # Return the reply to the client
        return web.json_response({"reply": reply, "conversation_id": conversation_id})

    except Exception as e:
        print(f"Error processing chat request: {e}\n{traceback.format_exc()}")
        return web.json_response({"error": "An internal server error occurred."}, status=500)


# --- Server Setup ---
def setup_server():
    """Creates and configures the aiohttp application."""
    app = web.Application()
    app.router.add_post('/chat', handle_chat)
    print("'/chat' route (POST) added.")
    return app

# --- Main Execution Block ---
if __name__ == '__main__':
    host = os.getenv("API_HOST", "127.0.0.1") # Default to localhost
    port = int(os.getenv("API_PORT", 8081))   # Default to port 8081
    
    app = setup_server()

    print(f"Starting API server on http://{host}:{port}")
    try:
        web.run_app(app, host=host, port=port)
    except Exception as e:
        print(f"Failed to start server: {e}") 
