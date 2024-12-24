from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime,date,timezone, timedelta

from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())
import os

SESSION_EXPIRE_TIME = os.getenv("SESSION_EXPIRE_TIME") or 7200
    
class Session_by_email_phone(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    active_session_id: str
    region_id: Optional[str] = None
    branch:Optional[str]=None
    whatsapp_number: Optional[str] = None
    organization_email: Optional[str] = None
    organization_id: Optional[str] = None
    created_date: datetime
    expires_at: Optional[datetime] = datetime.now(timezone.utc) + timedelta(seconds=int(SESSION_EXPIRE_TIME))




class Visitor(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    sender: str 
    agent: Optional[list] = []
    details:Optional[dict]={}
    organization_id:Optional[str]=None
    branch:Optional[str]=None
    region_id: Optional[str] = None
    created_date: datetime
    updated_date: datetime
    def __init__(self, **data):
        super().__init__(**data)
        self.id = self.sender  # Set id to sender
    
    
class Message(BaseModel):
    sender: Optional[str] = None
    agent:Optional[str] = None
    human_message:Optional[str] = None
    ai_message: Optional[str] = None
    organization_id:Optional[str]=None
    branch:Optional[str]=None
    handled:Optional[bool]=True
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    intent:Optional[str]=None
    whatsapp_number: Optional[str]=None
    region_id: Optional[str]=None
    initialFlag: Optional[bool] = False


class LeadPostRequest(BaseModel):
    sender: Optional[str] = None
    agent:Optional[str] = None
    ai_message: Optional[str] = None
    organization_id:Optional[str]=None
    branch:Optional[str]=None
    whatsapp_number: Optional[str]=None
    region_id: Optional[str] = None
    organization_email: Optional[str] = None
    initialFlag: Optional[bool] = False
    metadata: Optional[dict] = {}
    confirmation: Optional[bool] = True
    expire_time: Optional[datetime] = None