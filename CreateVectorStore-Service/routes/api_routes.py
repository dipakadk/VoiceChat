from fastapi import APIRouter,HTTPException,Query
from typing import List,Optional,Dict
from datetime import date, datetime,timedelta, timezone
from dotenv import load_dotenv
import csv
from fastapi.responses import StreamingResponse
from io import StringIO
from utils.utils import  validate_url,JSONEncoder
from services.visitor_create_db import get_chat_history,get_queries,query_group_pipeline,generate_visitor_pipeline,generate_lead_pipeline,upsert_visitor,create_visitors_session,upsert_session
from db.db_config import vectorstore_info_collection,visitor_leads,messages_collection,visitor_collection
from db.vector_store import VectorStoreInfoModel,VisitorLead
from services.web_extract_content import get_all_bind_urls
from bson import ObjectId
import json
from fastapi.concurrency import run_in_threadpool
import pandas as pd
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from db.db_config import clients, branches
from urllib.parse import urljoin, urlparse
from services.backgroundService import create_visitor_lead
from db.visitors import Message, LeadPostRequest, Visitor,Session_by_email_phone
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from services.backgroundService import confirmation_service

automation_url = os.getenv("AUTOMATION_URL")
authorization_id = os.getenv("CREATE_CONFIRMATION_AUTHORIZATION_TOKEN")

social_media = [
    'https://www.puregym.com/blog/',
    'https://x.com/',
    'https://www.facebook.com/',
    'https://twitter.com/',
    'https://www.instagram.com/',
    'https://www.linkedin.com/',
    'https://www.youtube.com/',
    'https://www.tiktok.com/'
]
blog_keywords = ['blog', 'article', 'posts']


load_dotenv()
router = APIRouter()

# Function to extract links using Selenium (Non-async function)
def extract_links_blocking(url: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
    )
    
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    links = [urljoin(url, link) for link in links]

    filtered_links = [
        link for link in links
        if urlparse(link).scheme in ['http', 'https'] and
           not any(sm in link for sm in social_media)
    ]
    
    return list(set(filtered_links))


#testing routes
@router.get('/test')
async def test_app():
    return {"message":"running"}


@router.get("/selenium/extract-links")
async def get_links(url: str = Query(..., description="The URL of the page to extract links from")):
    try:
        # Run Selenium in a threadpool to avoid blocking the event loop
        links = await run_in_threadpool(extract_links_blocking, url)
        return {"url": url, "links": links}
    except Exception as e:
        return {"error": str(e)}


from typing import List, Optional, Union
@router.get("/extract/url")
async def extract_url(url: str):
    try:
        await validate_url(url)
        documents = get_all_bind_urls(url)
        return {"urls": documents}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}
    


def encode_mongo_document(doc):
    # Function to convert MongoDB document to JSON serializable format
    return {k: (v if v is not None else None) for k, v in doc.items()}


# Route to download unique leads by sender in CSV format
@router.get("/visitor-leads/download")
async def download_unique_leads(
    organization_id: Optional[str] = None,
    branch: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    filters = {}
    filters = {"cancel_book": {"$ne": True}}
    
    # Apply filters based on query parameters
    if organization_id:
        filters["organization_id"] = organization_id
    if branch:
        filters["branch"] = branch
    if start_date or end_date:
        filters["created_date"] = {}
        if start_date:
            filters["created_date"]["$gte"] = start_date
        if end_date:
            filters["created_date"]["$lte"] = end_date

    # Aggregation pipeline to get unique leads
    pipeline = [
        {"$match": filters}, 
        {"$sort": {"sender": 1, "created_date": -1}}, 
        {"$group": {
            "_id": "$sender",
            "latest_doc": {"$first": "$$ROOT"} 
        }},
        {"$replaceRoot": {"newRoot": "$latest_doc"}} ,
        {"$sort": {"created_date": -1}}
    ]

    # Execute the aggregation pipeline
    leads_cursor = visitor_leads.aggregate(pipeline)
    leads = await leads_cursor.to_list(length=None)  # Fetch all leads
    print("leads is ==============",leads)
    if leads:
        df = pd.DataFrame(leads)

        client_name = ""
        branch_location = None
        if branch:
            branch_data = await branches.find_one({"_id": ObjectId(branch)})
            if branch_data:
                branch_location = branch_data.get("name", "")
                client_id = str(branch_data.get("client"))
                if client_id:
                    client_data = await clients.find_one({"_id": ObjectId(client_id)})
                    if client_data:
                        client_name = client_data.get("name", "")
        else:
            client_data = await clients.find_one({"_id": ObjectId(organization_id)})
            if client_data:
                client_name = client_data.get("name", "")
        df["Client"] = client_name
        df["Location"] = branch_location
        required_columns = ["Name", "email", "phone", "source_group", "type", "created_date"]

        df["Name"] = df["first_name"] + " " + df["last_name"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
        df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce").dt.strftime("%B %d %Y")
        df = df.rename(columns={
            "Name":"Name",
            "email": "Email",
            "phone": "Phone",
            "source_group": "Channel",
            "type": "Status",
            "created_date": "Date"
        })
        df = df[['Client','Location', "Date",'Name', "Email", "Phone", "Channel", "Status"]]
        df["Phone"] = df["Phone"].astype(str).apply(lambda x: '\t' + x.strip())

        
    else:
         df = pd.DataFrame(columns=["Client","Location", "Date","Name", "Email", "Phone", "Channel", "Status"])

    temp_csv_path = "./temp_csv.csv"
    csv_buffer = StringIO()
    df.to_csv(temp_csv_path, index=False, encoding="utf-8")
    ansi_csv = pd.read_csv(temp_csv_path, encoding='ANSI')
    ansi_csv.to_csv(csv_buffer, encoding='utf-8-sig', index=False)
    csv_buffer.seek(0)  # Rewind the buffer to the beginning
    response = StreamingResponse(csv_buffer, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=unique_visitor_leads.csv"
    os.remove(temp_csv_path)
    return response

@router.get("/visitor-leads/")
async def get_visitor_leads(
    organization_id: Optional[str] = None,
    branch: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    sender: Optional[str] = None,
    types: Optional[str] = None,
    source_group: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(10, description="Number of records to return", ge=1),
    offset: int = Query(0, description="Number of records to skip", ge=0),
):
    filters = {}
    filters = {"cancel_book": {"$ne": True}}
    
    # Apply filters for organization, email, phone, etc.
    if organization_id:
        filters["organization_id"] = organization_id
    if email:
        filters["email"] = email
    if phone:
        filters["phone"] = phone
    if sender:
        filters["sender"] = sender
    if types:
        filters["type"] = types
    if branch:
        filters["branch"] = branch
    if source_group:
        filters["source_group"] = source_group

    # Date filtering
    if start_date or end_date:
        filters["created_date"] = {}
        if start_date:
            filters["created_date"]["$gte"] = start_date
        if end_date:
            filters["created_date"]["$lte"] = end_date

    pipeline = [
    {"$match": filters},  
    {"$sort": {"created_date": -1}},  
    {"$group": {"_id": "$sender", "doc": {"$first": "$$ROOT"}}},  
    {"$replaceRoot": {"newRoot": "$doc"}},  
    {"$sort": {"created_date": -1}},  
    {"$skip": offset},  
    {"$limit": limit}
]

    # Execute the aggregation pipeline
    leads_cursor = visitor_leads.aggregate(pipeline)
    leads = await leads_cursor.to_list(length=limit)
    leads = [encode_mongo_document(doc) for doc in leads]  # Assuming encode_mongo_document is used for serialization

    # Count total unique senders
    total_leads_cursor = visitor_leads.aggregate([
        {"$match": filters},
        {"$group": {"_id": "$sender"}},
        {"$count": "total"}
    ])
    
    total_leads = await total_leads_cursor.to_list(length=1)
    total_count = total_leads[0]["total"] if total_leads else 0

    # Count documents by type dynamically
    type_pipeline = [
        {"$match": filters},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}}
    ]
    
    # Execute the aggregation pipeline to count types
    type_counts_cursor = visitor_leads.aggregate(type_pipeline)
    type_counts = await type_counts_cursor.to_list(length=None)  # Fetch all type counts
    
    # Convert the list of type counts to a dictionary for easy access
    type_count_dict = {doc["_id"]: doc["count"] for doc in type_counts if doc["_id"] is not None}

    return {
        "success": True,
        "total": total_count,
        "type_counts": type_count_dict,
        "page_size": len(leads),
        "data": leads
    }



@router.get("/vectordb/history")
async def get_files(
    organization_id: Optional[str] = Query(None, description="Organization ID"),
    branch: Optional[str] = Query(None, description="Branch"),
    region_id:Optional[str] = Query(None, description="Region"),
    deleted: Optional[bool] = Query(False, description="Document replaced"),
    uploaded_by: Optional[str] = Query(None, description="Uploaded By"),
    upload_date: Optional[date] = Query(None, description="Upload Date (YYYY-MM-DD)", example="2024-08-14"),
    limit: int = Query(10, description="Number of records to return", ge=1),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    try:
        filters = {}
        if organization_id:
            filters["organization_id"] = organization_id
        if branch:
            filters["branch"] = branch
        if region_id:
            filters["region_id"] = region_id
        if uploaded_by:
            filters["uploaded_by"] = uploaded_by
        filters["replaced"] = deleted

        if upload_date:
            upload_date_start = datetime(upload_date.year, upload_date.month, upload_date.day)
            upload_date_end = datetime(upload_date.year, upload_date.month, upload_date.day, 23, 59, 59)
            filters["files.upload_date"] = {
                "$gte": upload_date_start,
                "$lte": upload_date_end
            }

        cursor = vectorstore_info_collection.find(filters)
        file_info = await cursor.skip(offset).limit(limit).to_list(length=limit)  
        total_store = await vectorstore_info_collection.count_documents(filters)
        result_data = [VectorStoreInfoModel(**item) for item in file_info]

        return {"success": True, "total": total_store, "data": result_data}

    except Exception as e:
        return {"success": False, "message": str(e)}

def encode_mongo_document(document):
    """Encodes MongoDB documents by converting ObjectId and datetime."""
    for key, value in document.items():
        if isinstance(value, ObjectId):
            document[key] = str(value)
        elif isinstance(value, datetime):
            document[key] = value.isoformat()
        elif isinstance(value, list):  # Process list items
            document[key] = [encode_mongo_document(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):  # Recursively process nested dicts
            document[key] = encode_mongo_document(value)
    return document


def make_hashable(obj):
    """
    Recursively converts lists in a dictionary to tuples to make it hashable.
    """
    if isinstance(obj, dict):
        return frozenset((key, make_hashable(value)) for key, value in obj.items())
    elif isinstance(obj, list):
        return tuple(make_hashable(item) for item in obj)
    else:
        return obj

@router.get("/visitors_with_history")
async def get_visitors_with_history(    
    organization_id: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    region_ids: Optional[List[str]]=Query(None),
    agents: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    try:
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        if region_ids and branch:
            raise HTTPException(status_code=400, detail=("List of Region IDs and Branch ID both recieved."))

        history = await get_chat_history(organization_id,start_date, end_date,agents,branch,region_ids=region_ids )
        # print(history)
        encoded_history = [encode_mongo_document(doc) for doc in history]
        print("Before removing duplicates========================",len(encoded_history))
        if encoded_history:
            unique_visitors = list({make_hashable(visitor): visitor for visitor in encoded_history}.values())
            encoded_history = unique_visitors
        
        print("After removing duplicates======================================",len(encoded_history))

        return {"success":True,"total":len(encoded_history),"visitors":encoded_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/group/query/count_by_agent")
async def get_messages_by_agent(
    organization_id: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    try:
        # Set default dates
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Generate pipelines
        
        message_pipeline = query_group_pipeline(organization_id, start_date, end_date, branch)
        visitor_pipeline = generate_visitor_pipeline(organization_id, start_date, end_date, branch)
        lead_pipeline = generate_lead_pipeline(organization_id, start_date, end_date, branch)
        print("pipeline created")
        # Run queries concurrently using asyncio.gather
        messages_result, visitors_result, leads_result = await asyncio.gather(
            messages_collection.aggregate(message_pipeline).to_list(None),
            visitor_collection.aggregate(visitor_pipeline).to_list(None),
            visitor_leads.aggregate(lead_pipeline).to_list(None)
        )
        
        # Format lead response
        def format_lead_response(lead_results: List[Dict]) -> Dict:
            total_leads = sum(group.get("total_by_type", 0) for group in lead_results)
            formatted_response = {
                "total_leads": total_leads,
                "type_summary": []
            }
            for result in lead_results:
                lead_type = result["_id"]
                if lead_type.lower() == "lead":
                    lead_type = "Enquiries"
                elif lead_type.lower() == "tour":
                    lead_type = "Tours"
                elif lead_type.lower() == "trial":
                    lead_type = "Trials"
                type_data = {
                    "type": lead_type,
                    "total_count": result["total_by_type"],
                    "lead_summary": result["grouped_data"]
                }
                formatted_response["type_summary"].append(type_data)
            return formatted_response
        
        # Processing results...
        total_messages = sum(doc['message_count'] for doc in messages_result)
        total_visitors = sum(doc['visitor_count'] for doc in visitors_result)
        leads_summary = format_lead_response(leads_result)

        # Return response
        return {
            "success": True,
            "total_messages": total_messages,
            "message_summary": messages_result,
            "total_visitors": total_visitors,
            "visitor_summary": visitors_result,
            "total_leads": leads_summary.get("total_leads", 0),
            "leads_summary": leads_summary,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to get queries with different filters
@router.get("/history/get/queries")
async def get_history(
    handled: Optional[bool] = Query(None, description="Filter by handled status"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    region_id: Optional[str] = Query(None, description="Filter by Region ID"),
    limit: int = Query(10, description="Number of records to return", ge=1),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    try:
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        history_data = await get_queries(handled, start_date, end_date, organization_id,branch, limit, offset,region_id)
        queries = [entry.get("human_message", "") for entry in history_data]
        queries_details = json.loads(json.dumps(history_data, cls=JSONEncoder)) or []
        queries=json.loads(json.dumps(queries, cls=JSONEncoder)) or []
        return {"success":True,"total":len(queries),"queries":queries,"queries_details":queries_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/delete/lead")
async def delete_lead(lead_id:Optional[str] = None):
    try:
        if not ObjectId.is_valid(lead_id):
            print("Invalid Object ID")
            return {"success": False, "message": "Invalid Object ID"}
        result = await visitor_leads.delete_one({"_id": ObjectId(lead_id)})
        print(result)
        if result.deleted_count > 0:
            print("Succesfully Deleted Lead")
            return {"success": True, "message": f"Successfully Deleted Lead detail of ID {lead_id}"}
        else:
            print("No ID Found")
            return {"success": False, "message": f"No such Lead Found with ID {lead_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import json
@router.get("/create/booking/visitorleads")
async def create_visitor_leads(
    request: VisitorLead
):
    try:
        print(request)
        startDate = request.start_date
        time = request.time
        Email = request.email
        endDate = request.end_date
        convertedDate = request.converted_date
        venueName = request.venue_name
        firstName = request.first_name
        lastName = request.last_name
        Phonenumber = request.phone
        note = request.note
        sourceGroup = request.source_group
        clientId = request.organization_id
        branchId = request.branch
        sender = request.sender
        venueID = request.venue_id
        type_ = request.type
        print("==========",Phonenumber)
        json_note = json.loads(note)
        messages = ""
        if json_note:
            for i in range(len(json_note)):
                if json_note[i]['role'] == "user":
                    user_message = json_note[i]['content']
                    ai_message = json_note[i - 1]['content'] if i > 0 and json_note[i - 1]['role'] == 'assistant' else ""
                    # messages.append({"assistant": ai_message,"user": user_message})         
                    messages += f"<p>AI: {ai_message.replace('<p>','').replace('</p>','')}</p><p>Human: {user_message.replace('<p>','').replace('</p>','')}</p>"      

        # stringified_history = json.dumps(messages)
        mongo_data = {
            "start_date":startDate,
            "time":time,
            "email":Email,
            "end_date":endDate,
            "converted_date":convertedDate,
            "venue_name":venueName,
            "first_name":firstName ,
            "last_name":lastName,
            "phone":Phonenumber,    
            "source_group":sourceGroup,
            "source_name": "AI Agent",
            "type": (str(type_).capitalize() if type_ else "Tour"),
            "salesperson": "James Smith",
            "interested_in": "Fitness, Personal Training",
            "form_name": "Visitor Free Class Form",
            "organization_id":clientId,
            "branch":branchId,
            "created_date": datetime.now(timezone.utc),
            "updated_date": datetime.now(timezone.utc),
            "sender":sender,
            "venue_id":venueID,
            "confirm_book":True,
            "note": messages,
            "external_id": f"km{sender}"
        }
        data_mongo = VisitorLead(**mongo_data)
        lead_id = await create_visitor_lead(data_mongo.model_dump())
        if lead_id:
            print(f"Lead Created for ID {lead_id}")
            confirmation_url = automation_url+"/webhook/create_confirmation"
            response = confirmation_service(confirmation_url=confirmation_url, lead_id=lead_id)
            print(response,"response============from lead vapi")
            return {"success": True, "data":mongo_data, "_id":lead_id}
        else:
            return {"success": False, "error": "Lead ID not created"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


# visitor_data = Visitor(
#                         updated_date= datetime.now(timezone.utc),
#                         created_date= datetime.now(timezone.utc),
#                         sender=self.sender,
#                         organization_id=self.org_id,
#                         agent=[self.agent or "web"],
#                         details={
#                             "first_name":firstname,
#                             "last_name":lastname,
#                             "phone_number":phonenumber,
#                             "email_address":email
#                         }
#                     )


@router.post("/create/whatsapp/initialmessage")
async def createInitialWhatsappMessage(
    request: LeadPostRequest
):
    try:
        
        print("Request body recieved in LLM is==================",request)

        sender = request.sender or None
        agent = request.agent or None
        ai_message = request.ai_message or None
        organization_id = request.organization_id or None
        branch = request.branch or None
        whatsapp_number = request.whatsapp_number or None
        initialFlag = request.initialFlag or None
        region_id = request.region_id or None
        organization_email = request.organization_email or None

        metadata = request.metadata or {}

        first_name = metadata.get("first_name","")
        last_name = metadata.get("last_name", "")
        phone_number = metadata.get("phone","")
        email = metadata.get("email","")

        expires_at = request.expire_time

        confirmation_flag = request.confirmation or True

        try:
            session_data = Session_by_email_phone(
                    email = email,
                    phone=phone_number.replace("+", ""),
                    active_session_id=sender,
                    region_id=region_id,
                    branch=branch,
                    whatsapp_number=whatsapp_number,
                    organization_email=organization_email,
                    organization_id=organization_id,
                    expires_at=expires_at,
                    created_date=datetime.now(timezone.utc)
                )

            session_result = await upsert_session(session_data=session_data)
        
        except Exception as e:
            print("Error in Session Update")
            print("Session=======================",str(e))
        finally:
            print("Succesfully upserted session")


        if confirmation_flag:
            try:
                visitor_detail = Visitor(
                    updated_date=datetime.now(timezone.utc),
                    created_date = datetime.now(timezone.utc),
                    sender=sender,
                    organization_id=organization_id,
                    agent=[agent],
                    branch=branch,
                    region_id=region_id,
                    details = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": phone_number,
                        "email_address": email
                    }
                )
                updated_result = await upsert_visitor(visitor=visitor_detail)
            except Exception as e:
                print("Visitor lead update failed")
                print("Reason for fail==========",str(e))
            finally:
                print("Successfully updated Visitor Data===============",updated_result)
            
            try:
                message = Message(
                    sender=sender,
                    agent=agent,
                    human_message=None,
                    ai_message=ai_message,
                    organization_id=organization_id,
                    branch=branch,
                    region_id=None,
                    created_date=datetime.now(timezone.utc),
                    updated_date=datetime.now(timezone.utc),
                    handled=True,
                    intent=None,
                    whatsapp_number=whatsapp_number,
                    initialFlag=initialFlag
                )
                result = await messages_collection.insert_one(message.model_dump())
            except Exception as e:
                print("Message Update Failed")
                print("Reason for fail=======================",str(e))
        
        return {"success": True, "detail": "Succesfully updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 


