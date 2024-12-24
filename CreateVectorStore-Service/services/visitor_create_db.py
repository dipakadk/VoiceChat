from dotenv import load_dotenv, find_dotenv
from db.visitors import Visitor,Message,Session_by_email_phone
from db.db_config import visitor_collection,messages_collection,session_by_email_phone,visitor_leads
from pymongo import DESCENDING
load_dotenv(find_dotenv())
import os
from datetime import datetime,timezone,timedelta
from typing import List,Optional,Dict,Any
from db.vector_store import VisitorLead

SESSION_EXPIRE_TIME = os.getenv("SESSION_EXPIRE_TIME") or 7200

async def create_visitors_session(data):
    save_session=Session_by_email_phone(
        email=data.get('email_address') or None,
        phone=data.get('phone_number') or None,
        active_session_id=data.get('sender'),
        region_id=data.get("region_id") or None,
        branch=data.get('branch') or None,
        whatsapp_number=data.get("whatsapp_number") or None,
        organization_email = data.get("organization_email") or None,
        organization_id=data.get("organization_id") or None,
        created_date= datetime.now(timezone.utc),
        expires_at=data.get("expires_at") or datetime.now(timezone.utc) + timedelta(seconds=int(SESSION_EXPIRE_TIME))
    )
    saved_session=await session_by_email_phone.insert_one(save_session.model_dump())
    print("\n\n===========","=====================visitor session success fully in mongodb=======",saved_session,"\n\n")
    return True
    
    
async def get_active_session(email_phone: str=None, branch: Optional[str] = None, agent:str = None, whatsapp_number:str = None, organization_email:str=None):
    try:
        filters = {
            "$or": [
                {"phone": email_phone},           
                {"phone": f"+{email_phone}"},    
                {"email": email_phone}           
            ],
        }
        if whatsapp_number and agent in ["whatsapp", "sms"]:
            filters["whatsapp_number"] = whatsapp_number
        if organization_email and agent in ["email"]:
            filters["organization_email"] = organization_email

        
        result = await session_by_email_phone.find_one(
            filters,
            {"_id": 1, "phone": 1,"email":1, "active_session_id": 1, "branch":1, "organization_id":1,"region_id":1,"created_date":1},
            sort=[("created_date", -1)]
        )
        
        return result if result else None
    except Exception as e:
        print("Error fetching active session:", e)
        return None
    
    
    
async def get_visitor_details(visitor_id:str,organization_id:str=None,branch:str=None,region_id:str=None):
    filter = {"sender": visitor_id, "organization_id":organization_id}
    if branch:
        filter["branch"] = branch
    result = await visitor_collection.find_one(filter)
    if result:
        return result
    else:
        return None

async def get_visitor_lead_details(visitor_id:str, organization_id:str=None, branch:str=None):
    filter = {"sender": visitor_id, "organization_id": organization_id}
    if branch:
        filter["branch"] = branch
    result = await visitor_leads.find_one(filter, sort=[("created_date", -1)])
    if result:
        return result
    else:
        return None


async def upsert_visitor_leads(visitorlead, update_fields):
    try:
        query = {"sender": visitorlead.get("sender"), "organization_id":visitorlead.get('organization_id')}
        if visitorlead['branch']:
            query['branch'] = visitorlead.get("branch")
        most_recent_doc = await visitor_leads.find_one(query, sort=[("created_date", -1)])
        if most_recent_doc:
            query["_id"] = most_recent_doc["_id"]
        update_fields = {
            "$set": update_fields,
            "$setOnInsert":{
                "created_date": datetime.now(timezone.utc),
                "organization_id": visitorlead.get("organization_id"),
                "branch": visitorlead.get("branch"),
                "sender": visitorlead.get("sender")
            }
            }
        result = await visitor_leads.update_one(query, update_fields, upsert=True)
        if result.matched_count > 0:
            print("Document updated successfully.")
        elif result.upserted_id:
            print(f"New document created with ID: {result.upserted_id}")
        else:
            print("No document was updated or inserted.")
            
        return result
    except Exception as error:
        print(f"Error updating visitor lead in MongoDB: {error}")
        return None


async def upsert_session(session_data: Session_by_email_phone):
    try:
        query = {
            "active_session_id": session_data.active_session_id,
            "whatsapp_number": session_data.whatsapp_number,
        }

        update_fields = {
            "$set": {
                "active_session_id": session_data.active_session_id,
                "organization_id": session_data.organization_id,
                "branch": session_data.branch,
                "expires_at": session_data.expires_at,
                "phone": session_data.phone,
                "email": session_data.email,
                "whatsapp_number": session_data.whatsapp_number,
                "organization_email": session_data.organization_email

            },
            "$setOnInsert": {
                "created_date": session_data.created_date,

            }
        }

        result = await session_by_email_phone.update_one(query, update_fields, upsert=True)

        if result.matched_count > 0:
            print("Document updated successfully.")
        elif result.upserted_id:
            print(f"New document created with ID: {result.upserted_id}")
        else:
            print("No document was updated or inserted.")
        
        return result

    except Exception as error:
        print(f"Error in upserting session data: {error}")
        return None



    
async def upsert_visitor(visitor: Visitor):
    query = {"sender": visitor.sender,"organization_id":visitor.organization_id} 
    if visitor.branch:
       query['branch'] = visitor.branch # Use sender as the _id
    if visitor.region_id:
        query["region_id"] = visitor.region_id

    update_data = {
        "$addToSet": {
            "agent": {"$each": visitor.agent}
        },
        "$set": {
            "updated_date": datetime.now(timezone.utc)
        },
        "$setOnInsert": {
            "created_date": datetime.now(timezone.utc),
            "organization_id": visitor.organization_id,
            "branch": visitor.branch,
            "region_id":visitor.region_id,
            "sender": visitor.sender
        }
    }

    # Conditionally add details update if provided
    if visitor.details:
        cleaned_details = {
            key: ("" if value in {"N/A", "N\\A"} else value)
            for key, value in visitor.details.items()
        }
        update_data["$set"]["details"] = cleaned_details

    result = await visitor_collection.update_one(query, update_data, upsert=True)

    print("Updated result============================",result)
    
    return result.upserted_id or visitor.id



async def create_message(sender: str, human_message: str, ai_message: str, agent:str, organization_id: str=None, branch:Optional[str]=None,handled:Optional[bool]=True,intent:str=None, whatsapp_number:Optional[str]=None, region_id:Optional[str]=None) -> str:
    message = Message(
        sender=sender,
        agent=agent,
        human_message=human_message,
        ai_message=ai_message,
        organization_id=organization_id,
        branch=branch,
        region_id=region_id,
        created_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc),
        handled=handled,
        intent=intent,
        whatsapp_number=whatsapp_number
    )
    result = await messages_collection.insert_one(message.model_dump())
    print(result,"result")
    return str(result.inserted_id)


def generate_visitor_pipeline(
    organization_id: Optional[str],  
    start_date: Optional[datetime], 
    end_date: Optional[datetime],  
    branch: Optional[str],
) -> List[Dict]:
    pipeline = []

    match_stage = {}
    if organization_id:
        match_stage["organization_id"] = organization_id
    if branch:
        match_stage["branch"] = branch
    if start_date or end_date:
        match_stage["created_date"] = {}
        if start_date:
            match_stage["created_date"]["$gte"] = start_date
        if end_date:
            match_stage["created_date"]["$lte"] = end_date
    
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.append({"$unwind": "$agent"})

    pipeline.append({
        "$group": {
            "_id": "$agent",
            "visitor_count": {"$sum": 1} 
        }
    })

    pipeline.append({
        "$sort": {"visitor_count": DESCENDING}
    })

    return pipeline


def generate_lead_pipeline(
    organization_id: Optional[str],  
    start_date: Optional[datetime], 
    end_date: Optional[datetime],  
    branch: Optional[str],
) -> List[Dict]:
    pipeline = []
    match_stage = {}
    match_stage = {"cancel_book": {"$ne": True}}
    if organization_id:
        match_stage["organization_id"] = organization_id
    if branch:
        match_stage["branch"] = branch
    if start_date or end_date:
        match_stage["created_date"] = {}
        if start_date:
            match_stage["created_date"]["$gte"] = start_date
        if end_date:
            match_stage["created_date"]["$lte"] = end_date
    
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.append({
        "$group": {
            "_id": {
                "source_group": "$source_group", 
                "type": "$type"                
            },
            "lead_count": {"$sum": 1} 
        }
    })

    pipeline.append({
        "$group": {
            "_id": "$_id.type",
            "total_by_type": {"$sum": "$lead_count"}, 
            "grouped_data": {
                "$push": {
                    "source_group": "$_id.source_group",
                    "lead_count": "$lead_count"
                }
            }
        }
    })

    pipeline.append({
        "$sort": {"total_by_type": DESCENDING}
    })

    return pipeline

def query_group_pipeline(
    organization_id: Optional[str], 
    start_date: Optional[datetime], 
    end_date: Optional[datetime],  
    branch: Optional[str], 
) -> List[Dict]:
    pipeline = []

    match_stage = {}
    if organization_id:
        match_stage["organization_id"] = organization_id
    if branch:
        match_stage["branch"] = branch
    if start_date or end_date:
        match_stage["created_date"] = {}
        if start_date:
            match_stage["created_date"]["$gte"] = start_date
        if end_date:
            match_stage["created_date"]["$lte"] = end_date
    
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.append({
        "$group": {
            "_id": "$agent",
            "message_count": {"$sum": 1},
            "handled_count": {"$sum": {"$cond": ["$handled", 1, 0]}}
        }
    })

    pipeline.append({
        "$sort": {"message_count": DESCENDING}
    })

    return pipeline


async def generate_pipeline(organization_id: Optional[str],start_date: Optional[datetime], end_date: Optional[datetime],agent: Optional[List[str]],branch: Optional[str],region_ids:Optional[List[str]]):
    agents = await visitor_collection.distinct("agent")
    # region_ids = await visitor_collection.distinct("region_id")
    print(agents)
    pipeline = []
    match_stage = {}
    if agent:
        match_stage["agent"] = {"$in": agent}
    if organization_id:
        match_stage["organization_id"] = organization_id
    if region_ids:
        match_stage["region_id"] = {"$in": region_ids}
    elif branch:
        match_stage["branch"] = branch

    if start_date or end_date:
        match_stage["created_date"] = {}
        if start_date:
            match_stage["created_date"]["$gte"] = start_date
        if end_date:
            match_stage["created_date"]["$lte"] = end_date
    
    # print("==========matchstage",match_stage)
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.append(
        {
        "$lookup": {
            "from": "history",
            "let": {
                "sender": "$sender",
                "branch": "$branch",
                "organization_id": "$organization_id",
            },
            "pipeline": [
                {
                    "$match": {
                        "$expr": {
                            "$and": [
                                { "$eq": ["$sender", "$$sender"] },
                                { "$eq": ["$branch", "$$branch"] },
                                { "$eq": ["$organization_id", "$$organization_id"] }
                            ]
                            },
                        }
                    },

                ],
                "as": "history"
            }
        }
    )
    pipeline.append({
        "$lookup": {
            "from": "visitor_leads",
            "localField": "sender",
            "foreignField": "sender",
            "as": "leads"
        }
    })


    
    # Add fields dynamically based on the agents
    add_fields_stage = {"$addFields": {}}
    for agent in agents:
        if agent:
            field_name = f"{agent.lower()}"
            add_fields_stage["$addFields"][field_name] = {
                "$filter": {
                    "input": "$history",
                    "as": "h",
                    "cond": {"$eq": ["$$h.agent", agent]}
                }
            }
    # print(add_fields_stage)
    
    # Append the addFields stage to the pipeline
    pipeline.append(add_fields_stage)
    
    pipeline.append({
        "$unset": [
            "details.gdprLlm",
            "details.type"
        ]
    })

    
    # Project only the relevant fields
    project_stage = {
        "$project": {
            "_id": 0,
            "sender": 1,
            "agent":1,
            "details": 1,
            "organization_id": 1,
            "branch":1,
             "leads": 1
        }
    }

    for agent in agents:
        if agent:
            if agent.lower() not in ["whatsapp", "sms"]:
                pipeline.append({"$sort": {"created_date": -1}})
            project_stage["$project"][f"{agent.lower()}"] = 1

    pipeline.append(project_stage)

    
    print("pipeline==============================",pipeline)

    return pipeline

async def get_chat_history(
    organization_id: Optional[str]=None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agents: Optional[List[str]] = None,
    branch: Optional[str] = None,
    region_ids: Optional[List[str]] = None
):
    # Ensure generate_pipeline is awaited if it's async
    pipeline = await generate_pipeline(organization_id, start_date, end_date, agents, branch,region_ids=region_ids)

    # Use async aggregation and await for results
    cursor = visitor_collection.aggregate(pipeline)
    # print("cursor====",cursor)
    results = await cursor.to_list(length=None)

    # print("results===",results)
    
    return results



async def get_queries(handled: Optional[bool], start_date: Optional[datetime], end_date: Optional[datetime], organization_id: Optional[str], branch: Optional[str], limit: int, offset: int,region_id: Optional[str]):
    query = {}

    if handled is not None:
        query["handled"] = handled
    
    if organization_id:
        query["organization_id"] = organization_id
    if branch:
        query["branch"] = branch
    if region_id:
        query["region_id"] = region_id
    if start_date or end_date:
        query["created_date"] = {}
        if start_date:
            query["created_date"]["$gte"] = start_date
        if end_date:
            query["created_date"]["$lte"] = end_date
    query["intent"] = {"$nin": [None, "", " "]}

    # Perform the query and convert the cursor to a list
    cursor = messages_collection.find(
        query, 
        {"human_message": 1, "ai_message": 1, "organization_id": 1, "handled": 1,"sender":1 ,"agent": 1, "_id": 1, "intent": 1}
    ).skip(offset).limit(limit)

    # Convert cursor to list
    results = await cursor.to_list(None)

    return results
