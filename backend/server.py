from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from openai import AsyncOpenAI

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class QuestionResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "DSA Interview Assistant API"}

@api_router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    try:
        # Get or create conversation
        conversation_id = request.conversation_id
        
        if conversation_id:
            # Get existing conversation
            conv_data = await db.conversations.find_one({"id": conversation_id})
            if not conv_data:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation = Conversation(**conv_data)
        else:
            # Create new conversation
            conversation = Conversation()
            await db.conversations.insert_one(conversation.dict())
            conversation_id = conversation.id
        
        # Initialize LLM Chat with context from previous messages
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="API key not configured")
        
        # Create system message optimized for DSA and coding interviews
        system_message = """You are an expert DSA and coding interview assistant. 
Provide concise, direct answers with code examples when relevant.
For coding questions:
- Give clean, optimized code solutions
- Use proper syntax highlighting with language tags (```python, ```javascript, etc.)
- Explain time and space complexity briefly
- Keep explanations short and to the point
For interview questions:
- Provide structured, professional answers
- Focus on key points
- Be concise but complete"""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=conversation_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        # Create user message
        user_msg = UserMessage(text=request.question)
        
        # Get response from LLM
        response = await chat.send_message(user_msg)
        
        # Create message objects
        user_message = Message(
            role="user",
            content=request.question
        )
        
        assistant_message = Message(
            role="assistant",
            content=response
        )
        
        # Update conversation
        conversation.messages.append(user_message)
        conversation.messages.append(assistant_message)
        conversation.updated_at = datetime.utcnow()
        
        # Generate title from first question if it's a new conversation
        if len(conversation.messages) == 2:  # First Q&A pair
            title = request.question[:50] + "..." if len(request.question) > 50 else request.question
            conversation.title = title
        
        # Update in database
        await db.conversations.update_one(
            {"id": conversation_id},
            {"$set": conversation.dict()}
        )
        
        return QuestionResponse(
            answer=response,
            conversation_id=conversation_id,
            message_id=assistant_message.id
        )
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations", response_model=List[Conversation])
async def get_conversations():
    try:
        conversations = await db.conversations.find().sort("updated_at", -1).to_list(100)
        return [Conversation(**conv) for conv in conversations]
    except Exception as e:
        logging.error(f"Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    try:
        conv_data = await db.conversations.find_one({"id": conversation_id})
        if not conv_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Conversation(**conv_data)
    except Exception as e:
        logging.error(f"Error fetching conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    try:
        result = await db.conversations.delete_one({"id": conversation_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()