import streamlit as st
import json
from datetime import datetime
import os
import dotenv
import re
import traceback

# --- LangChain & Dr. Mind Agent Imports (from screening.py) ---
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool

# --- Environment Setup ---
dotenv.load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") or os.getenv("API_BASE")

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if OPENAI_API_BASE:
    os.environ["OPENAI_API_BASE"] = OPENAI_API_BASE

# --- FAISS Index Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(current_dir, "screening", "faiss_index")
faiss_file = os.path.join(FAISS_INDEX_PATH, "index.faiss")
pkl_file = os.path.join(FAISS_INDEX_PATH, "index.pkl")

chat_model = None
embeddings_model = None
retriever_tool = None
vector_store = None

try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

try:
    chat_model = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7
    )
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        openai_api_base=os.environ.get("OPENAI_API_BASE")
    )
    # Try to load FAISS index
    if os.path.exists(faiss_file) and os.path.exists(pkl_file):
        vector_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings_model)
    else:
        # Fallback: create sample disorders
        from langchain.docstore.document import Document
        sample_texts = [
            '{"name": "Major Depressive Disorder", "criteria": "A. Five (or more) of the following symptoms..."}',
            '{"name": "Generalized Anxiety Disorder", "criteria": "A. Excessive anxiety and worry..."}',
            '{"name": "Normal", "criteria": "The individual does not meet criteria for any mental disorder..."}'
        ]
        sample_docs = [Document(page_content=text) for text in sample_texts]
        vector_store = FAISS.from_documents(sample_docs, embeddings_model)
    def search_and_print(query: str) -> str:
        try:
            docs = vector_store.similarity_search(query, k=3)
            results = "\n".join([doc.page_content for doc in docs])
            return f"<<<RETRIEVAL_RESULTS>>>\n{results}\n<<<END_RETRIEVAL>>>"
        except Exception as e:
            return f"Error retrieving information: {str(e)}"
    retriever_tool = Tool(
        name="search_document_database",
        description="Searches and returns relevant information from the document database based on the user query.",
        func=search_and_print,
    )
except Exception as e:
    chat_model = None
    retriever_tool = None
    st.error(f"Error initializing Dr. Mind agent: {e}")

# --- Dr. Mind Prompt (from screening.py) ---
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
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# --- Dr. Mind Agent Executor ---
agent = None
agent_executor = None
if chat_model and retriever_tool:
    tools = [retriever_tool]
    agent = create_openai_tools_agent(chat_model, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

# --- Conversation Memory for Streamlit Sessions ---
class InMemoryChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
    def add_message(self, message):
        self.messages.append(message)
    def clear(self):
        self.messages = []

conversation_memory_store = {}
def get_memory(session_id: str):
    if session_id not in conversation_memory_store:
        conversation_memory_store[session_id] = InMemoryChatMessageHistory(session_id=session_id)
    return conversation_memory_store[session_id]

agent_with_history = None
if agent_executor:
    agent_with_history = RunnableWithMessageHistory(
        agent_executor,
        get_memory,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

# --- Streamlit Session State Initialization ---
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_state" not in st.session_state:
        st.session_state.chat_state = "screening"
    if "diagnosis" not in st.session_state:
        st.session_state.diagnosis = {
            "possible_conditions": [],
            "assessment_results": {},
            "final_diagnosis": "",
            "recommendations": ""
        }
    if "current_assessment" not in st.session_state:
        st.session_state.current_assessment = None
    if "assessment_responses" not in st.session_state:
        st.session_state.assessment_responses = {}
    if "assessment_index" not in st.session_state:
        st.session_state.assessment_index = 0
    if "last_assessment" not in st.session_state:
        st.session_state.last_assessment = None
    if "report_generated" not in st.session_state:
        st.session_state.report_generated = False

# --- New Screening Agent (Dr. Mind) ---
def screening_agent(user_input):
    if not agent_with_history:
        st.error("Dr. Mind agent is not available. Please check your API key and FAISS index.")
        return "Sorry, the screening agent is currently unavailable."
    session_id = "streamlit-session"  # Could use st.session_state.session_id if you want per-user
    try:
        # Add user message to memory
        memory = get_memory(session_id)
        memory.add_message(HumanMessage(content=user_input))
        # Call the agent synchronously
        response = agent_with_history.invoke({"input": user_input}, config={"configurable": {"session_id": session_id}})
        reply = response.get("output", "")
        # Add agent reply to memory
        memory.add_message(AIMessage(content=reply))
        st.session_state.messages.append({"role": "assistant", "content": reply})
        # Check for JSON diagnosis output
        json_match = re.search(r'\{.*\}', reply.replace('\n', ' '))
        if json_match:
            json_str = json_match.group(0)
            try:
                result = json.loads(json_str)
                if "result" in result:
                    # Screening complete, move to assessment or report
                    st.session_state.diagnosis["possible_conditions"] = result["result"]
                    st.session_state.chat_state = "assessment"
                    st.session_state.messages.append({"role": "assistant", "content": "Thank you for sharing your experiences. Based on your responses, I have a better understanding of your situation."})
            except Exception as e:
                st.warning(f"Could not parse Dr. Mind's JSON output: {e}")
        return reply
    except Exception as e:
        st.error(f"Error during screening: {e}\n{traceback.format_exc()}")
        return f"Sorry, an error occurred: {e}"

# --- Assessment Tools ---
ASSESSMENTS = {
    "DASS-21": {
        "name": "Depression Anxiety Stress Scales",
        "description": "Measures depression, anxiety, and stress levels",
        "questions": [
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
        ],
        "options": [
            "Did not apply to me at all",
            "Applied to me to some degree, or some of the time",
            "Applied to me to a considerable degree, or a good part of time",
            "Applied to me very much, or most of the time"
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
        ],
        "options": [
            "Did not apply to me at all",
            "Applied to me to some degree, or some of the time",
            "Applied to me to a considerable degree, or a good part of time",
            "Applied to me very much, or most of the time"
        ],
        "scores": [0, 1, 2, 3],
        "interpretation": {
            "stress": {
                "0-14": "Normal",
                "15-18": "Mild",
                "19-25": "Moderate",
                "26-33": "Severe",
                "34+": "Extremely Severe"
            },
            "anxiety": {
                "0-7": "Normal",
                "8-9": "Mild",
                "10-14": "Moderate",
                "15-19": "Severe",
                "20+": "Extremely Severe"
            },
            "depression": {
                "0-9": "Normal",
                "10-13": "Mild",
                "14-20": "Moderate",
                "21-27": "Severe",
                "28+": "Extremely Severe"
            },
            "stress": {
                "0-14": "Normal",
                "15-18": "Mild",
                "19-25": "Moderate",
                "26-33": "Severe",
                "34+": "Extremely Severe"
            },
            "anxiety": {
                "0-7": "Normal",
                "8-9": "Mild",
                "10-14": "Moderate",
                "15-19": "Severe",
                "20+": "Extremely Severe"
            },
            "depression": {
                "0-9": "Normal",
                "10-13": "Mild",
                "14-20": "Moderate",
                "21-27": "Severe",
                "28+": "Extremely Severe"
            }
        }
    },
    "PCL-5": {
        "name": "PTSD Checklist for DSM-5",
        "description": "Screens for PTSD symptoms",
        "questions": [
            "Repeated, disturbing, and unwanted memories of the stressful experience?",
            "Repeated, disturbing dreams of the stressful experience?",
            "Suddenly feeling or acting as if the stressful experience were actually happening again?",
            "Feeling very upset when something reminded you of the stressful experience?",
            "Having strong physical reactions when something reminded you of the stressful experience?",
            "Avoiding memories, thoughts, or feelings related to the stressful experience?",
            "Avoiding external reminders of the stressful experience?",
            "Trouble remembering important parts of the stressful experience?",
            "Having strong negative beliefs about yourself, other people, or the world?",
            "Blaming yourself or someone else for the stressful experience?",
            "Having strong negative feelings such as fear, horror, anger, guilt, or shame?",
            "Loss of interest in activities that you used to enjoy?",
            "Feeling distant or cut off from other people?",
            "Trouble experiencing positive feelings?",
            "Irritable behavior, angry outbursts, or acting aggressively?",
            "Taking too many risks or doing things that could cause you harm?",
            "Being 'superalert' or watchful or on guard?",
            "Feeling jumpy or easily startled?",
            "Having difficulty concentrating?",
            "Trouble falling or staying asleep?"
        ],
        "options": ["Not at all", "A little bit", "Moderately", "Quite a bit", "Extremely"],
        "scores": [0, 1, 2, 3, 4],
        "interpretation": {
            "0-31": "Below threshold for PTSD",
            "32-80": "Probable PTSD - clinical assessment recommended"
        }
    }
}

def calculate_dass_scores(responses):
    # DASS-21 scoring
    stress_items = [0, 5, 7, 10, 11, 13, 17]  # Q1, Q6, Q8, Q11, Q12, Q14, Q18
    anxiety_items = [1, 3, 6, 8, 14, 18, 19]  # Q2, Q4, Q7, Q9, Q15, Q19, Q20
    depression_items = [2, 4, 9, 12, 15, 16, 20]  # Q3, Q5, Q10, Q13, Q16, Q17, Q21
    
    stress_score = sum(responses[i] for i in stress_items) * 2
    anxiety_score = sum(responses[i] for i in anxiety_items) * 2
    depression_score = sum(responses[i] for i in depression_items) * 2
    
    return {
        "stress": stress_score,
        "anxiety": anxiety_score,
        "depression": depression_score
    }

def get_dass_interpretation(scores):
    interpretations = {}
    for category, score in scores.items():
        for range_str, level in ASSESSMENTS["DASS-21"]["interpretation"][category].items():
            min_score, max_score = map(int, range_str.split("-"))
            if min_score <= score <= max_score:
                interpretations[category] = level
                break
    return interpretations

def get_healthcare_recommendation(assessment_name, score_type, interpretation):
    recommendations = {
        "DASS-21": {
            "depression": {
                "Normal": "Your depression symptoms appear to be within normal range. Continue practicing self-care and maintaining healthy habits. If you notice any changes in your mood or symptoms, consider speaking with a healthcare provider.",
                "Mild": "You're experiencing mild depression symptoms. Consider implementing self-care strategies and monitoring your symptoms. If they persist or worsen, it may be helpful to speak with a healthcare provider.",
                "Moderate": "Your responses suggest moderate depression symptoms. It's recommended that you speak with a healthcare provider to discuss your symptoms and explore appropriate support options.",
                "Severe": "Your responses indicate severe depression symptoms. It's strongly recommended that you speak with a healthcare provider as soon as possible to discuss your symptoms and treatment options.",
                "Extremely Severe": "Your responses suggest extremely severe depression symptoms. Please seek immediate support from a healthcare provider or mental health professional. If you're having thoughts of self-harm, please contact emergency services or a crisis helpline immediately."
            },
            "anxiety": {
                "Normal": "Your anxiety symptoms appear to be within normal range. Continue practicing stress management techniques and maintaining healthy habits. If you notice any changes in your symptoms, consider speaking with a healthcare provider.",
                "Mild": "You're experiencing mild anxiety symptoms. Consider implementing stress management techniques and monitoring your symptoms. If they persist or worsen, it may be helpful to speak with a healthcare provider.",
                "Moderate": "Your responses suggest moderate anxiety symptoms. It's recommended that you speak with a healthcare provider to discuss your symptoms and explore appropriate support options.",
                "Severe": "Your responses indicate severe anxiety symptoms. It's strongly recommended that you speak with a healthcare provider as soon as possible to discuss your symptoms and treatment options.",
                "Extremely Severe": "Your responses suggest extremely severe anxiety symptoms. Please seek immediate support from a healthcare provider or mental health professional. If you're experiencing a panic attack or severe distress, please contact emergency services or a crisis helpline immediately."
            },
            "stress": {
                "Normal": "Your stress levels appear to be within normal range. Continue practicing stress management techniques and maintaining healthy habits. If you notice any changes in your stress levels, consider speaking with a healthcare provider.",
                "Mild": "You're experiencing mild stress. Consider implementing stress management techniques and monitoring your stress levels. If they persist or worsen, it may be helpful to speak with a healthcare provider.",
                "Moderate": "Your responses suggest moderate stress levels. It's recommended that you speak with a healthcare provider to discuss your stress management strategies and explore appropriate support options.",
                "Severe": "Your responses indicate severe stress levels. It's strongly recommended that you speak with a healthcare provider as soon as possible to discuss your symptoms and treatment options.",
                "Extremely Severe": "Your responses suggest extremely severe stress levels. Please seek immediate support from a healthcare provider or mental health professional. If you're experiencing severe distress, please contact emergency services or a crisis helpline immediately."
            }
        },
        "PCL-5": {
            "Below threshold for PTSD": "Your responses suggest that you are below the threshold for PTSD. However, if you're experiencing distress related to a traumatic event, speaking with a mental health professional can still be beneficial.",
            "Probable PTSD - clinical assessment recommended": "Your responses suggest you may be experiencing significant PTSD symptoms. It's strongly recommended that you speak with a mental health professional specializing in trauma for proper evaluation and support."
        }
    }
    if assessment_name == "DASS-21":
        return recommendations[assessment_name][score_type][interpretation]
    else:
        return recommendations[assessment_name][interpretation]

def get_assessment_priorities(conditions, current_assessment=None):
    priorities = []
    condition_map = {
        "depression": "DASS-21",
        "anxiety": "DASS-21",
        "stress": "DASS-21",
        "ptsd": "PCL-5"
    }
    for condition in conditions:
        condition = condition.lower()
        for key, assessment in condition_map.items():
            if key in condition and assessment not in st.session_state.diagnosis["assessment_results"] and assessment != current_assessment:
                priorities.append(assessment)
    return priorities

def calculate_assessment_results(assessment_data, responses):
    if assessment_data["name"] == "Depression Anxiety Stress Scales":
        scores = calculate_dass_scores(responses)
        interpretations = get_dass_interpretation(scores)
        return scores, interpretations
    else:
        total_score = sum(responses)
        interpretation = ""
        for score_range, interp in assessment_data["interpretation"].items():
            min_score, max_score = map(int, score_range.split("-"))
            if min_score <= total_score <= max_score:
                interpretation = interp
                break
        return total_score, interpretation

def assessment_agent():
    current = st.session_state.current_assessment
    assessment_data = ASSESSMENTS[current]
    if st.session_state.last_assessment != current:
        st.session_state.assessment_index = 0
        st.session_state.last_assessment = current
    if st.session_state.assessment_index < len(assessment_data["questions"]):
        question = assessment_data["questions"][st.session_state.assessment_index]
        st.markdown(f"**Question {st.session_state.assessment_index + 1}:** {question}")
        cols = st.columns(len(assessment_data["options"]))
        for i, col in enumerate(cols):
            if col.button(assessment_data["options"][i], key=f"option_{i}_{st.session_state.assessment_index}_{current}"):
                st.session_state.messages.append({"role": "assistant", "content": f"Question {st.session_state.assessment_index + 1}: {question}"})
                if current not in st.session_state.assessment_responses:
                    st.session_state.assessment_responses[current] = []
                score = assessment_data["scores"][i]
                st.session_state.assessment_responses[current].append(score)
                st.session_state.messages.append({"role": "user", "content": f"My answer: {assessment_data['options'][i]}"})
                st.session_state.assessment_index += 1
                if st.session_state.assessment_index >= len(assessment_data["questions"]):
                    if current == "DASS-21":
                        scores, interpretations = calculate_assessment_results(assessment_data, st.session_state.assessment_responses[current])
                        st.session_state.diagnosis["assessment_results"][current] = {
                            "scores": scores,
                            "interpretations": interpretations
                        }
                        result_message = f"""Thank you for completing the questionnaire. Here are your results:\n\nDepression Level: {interpretations['depression']}\nAnxiety Level: {interpretations['anxiety']}\nStress Level: {interpretations['stress']}\n\n**Healthcare Recommendations:**\n{get_healthcare_recommendation(current, 'depression', interpretations['depression'])}\n\n**Important Disclaimer:**\nThis questionnaire is a screening tool and not a clinical diagnosis. The chatbot cannot provide a real medical diagnosis and is not a substitute for professional healthcare. Please consult with a qualified healthcare provider for proper evaluation and treatment."""
                    else:
                        total_score, interpretation = calculate_assessment_results(assessment_data, st.session_state.assessment_responses[current])
                        st.session_state.diagnosis["assessment_results"][current] = {
                            "score": total_score,
                            "interpretation": interpretation
                        }
                        result_message = f"""Thank you for completing the questionnaire. Here are your results:\n\nScore: {total_score}\nInterpretation: {interpretation}\n\n**Healthcare Recommendation:**\n{get_healthcare_recommendation(current, total_score, interpretation)}\n\n**Important Disclaimer:**\nThis questionnaire is a screening tool and not a clinical diagnosis. The chatbot cannot provide a real medical diagnosis and is not a substitute for professional healthcare. Please consult with a qualified healthcare provider for proper evaluation and treatment."""
                    st.session_state.messages.append({"role": "assistant", "content": result_message})
                    assessment_priorities = get_assessment_priorities(st.session_state.diagnosis["possible_conditions"], current)
                    if assessment_priorities:
                        next_assessment = assessment_priorities[0]
                        st.session_state.current_assessment = next_assessment
                        st.session_state.assessment_index = 0
                        next_assessment_intro = "I have another questionnaire for you to complete. Please answer the following questions honestly."
                        st.session_state.messages.append({"role": "assistant", "content": next_assessment_intro})
                        st.rerun()
                    else:
                        st.session_state.chat_state = "awaiting_report"
                        completion_message = """Thank you for completing all the questionnaires.\n\nYou can now generate your comprehensive report by clicking the \"Generate Report\" button below. The report will include:\n1. A summary of your results\n2. Interpretation of your scores\n3. Recommendations for next steps\n4. Important information about seeking professional help\n\nWhen you're ready, click the button to generate your report."""
                        st.session_state.messages.append({"role": "assistant", "content": completion_message})
                        st.rerun()
                else:
                    st.rerun()
        return None
    return None

def follow_up_agent(user_input):
    follow_up_prompt = [
        {"role": "system", "content": """You are a mental health support specialist providing follow-up care after the initial assessment.\nYour role is to:\n1. Answer questions about the assessment results and report\n2. Provide additional information about mental health conditions\n3. Offer support and guidance\n4. Help clarify any concerns about the recommendations\n5. Encourage seeking professional help when appropriate\n6. Do not answer any questions that are not related to the report or the assessment or the mental health.\nIf the patient asks things that are not related to the report or the assessment or the mental health, please ask them to ask something related to the report or the assessment or the mental health.\n\nBe supportive, empathetic, and professional. Do not provide medical advice or diagnosis.\nRecommend the patient to seek professional help when appropriate.\nIf you detect an immediately URGENT SAFETY CONCERN such as (i want to die now), please send the following message:\n***\n1. **If you are in an immediately dangerous situation (such as on a rooftop, bridge, or with means of harm):**\n- Move to a safe location immediately\n- Call emergency services: 999\n- Stay on the line with emergency services\n\n2. **For immediate support:**\n- Go to your nearest emergency room/A&E department\n- Call The Samaritans hotline (Multilingual): (852) 2896 0000\n- Call Suicide Prevention Service hotline (Cantonese): (852) 2382 0000\n\n**Are you currently in a safe location?** If not, please seek immediate help using the emergency contacts above.\n***\n"""}
    ]
    for message in st.session_state.messages:
        if message["role"] in ["user", "assistant"]:
            follow_up_prompt.append(message)
    follow_up_prompt.append({"role": "user", "content": user_input})
    # Replace with your actual model call if needed
    response = user_input  # Placeholder: echo user input
    st.session_state.messages.append({"role": "assistant", "content": response})
    return response

def generate_report():
    report = f"""# Mental Health Assessment Report\n\n## Date: {datetime.now().strftime('%B %d, %Y')}\n\n### Assessment Results\n{json.dumps(st.session_state.diagnosis['assessment_results'], indent=2)}\n\n### Note\nThis is a sample report. Please consult a professional for a full evaluation."""
    st.session_state.messages.append({"role": "assistant", "content": report})
    st.session_state.report_generated = True
    st.session_state.chat_state = "follow_up"
    return report

# --- Streamlit UI ---
# Ensure session state is initialized before any access
initialize_session_state()

st.title("Mental Health Initial Diagnosis Chatbot")
chat_container = st.container()
if not st.session_state.messages:
    welcome_message1 = {
        "role": "assistant",
        "content": """Welcome to the Mental Health Chatbot.\n\n***I'm here to help assess your mental health and provide initial diagnosis. We'll start with a conversation to understand your concerns, then I may ask you to complete one or more standardized assessments, and finally I'll provide a report summarizing our findings.***\n\n***Please note that this is not a substitute for professional medical advice, diagnosis, or treatment. If you're experiencing a mental health emergency, please contact emergency services or a crisis helpline immediately.***\n\n***The conversation is confidential and will not be shared with anyone without your consent.***\n _________"""
    }
    st.session_state.messages.append(welcome_message1)
    welcome_message2 = {
        "role": "assistant",
        "content": "Hi, I am the Mental Health Diagnosis Chatbot, how are you feeling today?"
    }
    st.session_state.messages.append(welcome_message2)

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if st.session_state.messages:
        js = '''
        <script>
            function scrollToBottom() {
                const messages = document.querySelector('[data-testid="stChatMessageContainer"]');
                if (messages) {
                    messages.scrollTop = messages.scrollHeight;
                }
            }
            scrollToBottom();
        </script>
        '''
        st.components.v1.html(js, height=0)

user_input = st.chat_input("Type your message here...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    if st.session_state.chat_state == "screening":
        response = screening_agent(user_input)
    elif st.session_state.chat_state == "assessment":
        response = "I see you've sent a message during the assessment. Please use the buttons above to answer the current assessment question. If you need to stop the assessment, you can click 'Start New Conversation'."
        st.session_state.messages.append({"role": "assistant", "content": response})
    elif st.session_state.chat_state == "follow_up":
        response = follow_up_agent(user_input)
    else:
        response = "I'm not sure what to do with your message. Please try starting a new conversation."
        st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if st.session_state.chat_state == "assessment" and st.session_state.current_assessment:
    assessment_agent()

if st.session_state.chat_state == "awaiting_report":
    if st.button("Generate Report"):
        st.session_state.messages.append({"role": "assistant", "content": "Generating your comprehensive report..."})
        report = generate_report()
        st.rerun()

if st.button("Start New Conversation"):
    st.session_state.messages = []
    st.session_state.chat_state = "screening"
    st.session_state.diagnosis = {
        "possible_conditions": [],
        "assessment_results": {},
        "final_diagnosis": "",
        "recommendations": ""
    }
    st.session_state.current_assessment = None
    st.session_state.assessment_responses = {}
    st.session_state.assessment_index = 0
    st.rerun()

if st.checkbox("Show Debug Info"):
    st.write(f"Current State: {st.session_state.chat_state}")
    st.write(f"Current Assessment: {st.session_state.current_assessment}")
    st.write(f"Assessment Index: {st.session_state.assessment_index}")
    st.write(f"Diagnosis Data: {st.session_state.diagnosis}")
    st.write(f"Assessment Responses: {st.session_state.assessment_responses}") 