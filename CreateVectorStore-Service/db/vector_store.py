from typing import Optional, List, Dict
from pydantic import BaseModel,Field
from datetime import datetime,date

class FileMetadataModel(BaseModel):
    filename: str
    original_filename: str
    upload_date: datetime
    content_type: str
    s3_url: str

class VectorStoreInfoModel(BaseModel):
    files: List[FileMetadataModel]
    organization_id: str
    branch: Optional[str] = None
    uploaded_by:Optional[str]=None
    url: Optional[list] = None
    vectorstore_collection: str
    intent: Optional[str] = None
    created_date: datetime
    updated_date: datetime
    replaced:Optional[bool] = False
    region_id: Optional[str] = None
    
class VisitorLead(BaseModel):
    start_date: Optional[datetime] = None
    email: Optional[str] = None
    end_date: Optional[datetime] = None
    venue_name: Optional[str] = None
    first_name: Optional[str]=None
    last_name: Optional[str]=None
    phone: Optional[str] = None
    source_group: Optional[str] = "web"
    source_name: Optional[str] = "AI Agent"
    type: Optional[str] = "Others"
    salesperson: Optional[str] = None
    gender: Optional[str] =None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    dob: Optional[date]=None
    interested_in: Optional[str] = None
    referred_by: Optional[str] = None
    form_name: Optional[str] = None
    organization_id:Optional[str]=None
    branch:Optional[str]=None
    created_date: Optional[datetime]=None
    updated_date: Optional[datetime]=None
    confirm_book:Optional[bool]= True
    sender: Optional[str]=None
    cancel_book: Optional[bool] = False
    event_id: Optional[str]=None   
    time: Optional[str] = None
    converted_date:Optional[str] = None 
    venue_id: Optional[str] = None
    confirmation_sent_date: Optional[datetime] = None 
    note: Optional[str] = None
    external_id: Optional[str] = None
    expire_time: Optional[datetime] = None