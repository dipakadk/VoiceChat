from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class EmbeddingType(str, Enum):
    huggingface = "huggingface"
    openai = "openai"
    sentence_transformers = "sentence_transformers"
    
    

class StoreType(str, Enum):
    milvus = "milvus"
    chroma = "chroma"

class StoreArguments(BaseModel):
    data: list[dict[str, str]] = Field(
        ..., description="List of dictionaries containing data to store. Each dictionary should have a 'content' key with the actual content."
    )
    collection_name: str = Field(
        ..., description="Name of the collection to store the data in. Follows the format 'general_store_<id>'."
    )
    embedding_type: str = Field(
        "openai", description="Type of embedding to use. Defaults to 'openai'."
    )
    store_type: str = Field(
        "milvus", description="Type of storage to use. Defaults to 'milvus'."
    )
    host: str = Field(
        ..., description="Host address of the storage system."
    )
    port: int = Field(
        ..., description="Port number of the storage system."
    )
    
class QueryRequest(BaseModel):
    query: str
    sender: str
    org_id: Optional[str] = None
    stream: Optional[bool] = False
    agent: str
    metadata:dict={}
    organization_name:Optional[str] = None
    chatbot_name: Optional[str] = None
    branch: Optional[str] = None
    welcome_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    venue_id: Optional[str] = None
    region_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    useRegion: Optional[bool] = True
    organization_email: Optional[str] = None
    # response_content_line:Optional[int]=50
    # out_of_context_response: str 
    
class TrainingDataRequest(BaseModel):
    organization_id: Optional[str] = None
    message_id: Optional[str] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    intent: Optional[str] = None
    branch: Optional[str] = None
    region_id: Optional[str] = None