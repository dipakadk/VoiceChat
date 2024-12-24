from services.http_api import http_post
from db.vector_store import VisitorLead
from db.db_config import visitor_leads
from datetime import datetime, timezone

import json
import requests

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

automation_url = os.getenv("AUTOMATION_URL")
authorization_id = os.getenv("CREATE_CONFIRMATION_AUTHORIZATION_TOKEN")


async def create_visitor_lead(lead):
    try:
        result = await visitor_leads.insert_one(lead)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error inserting lead into MongoDB: {e}")
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
                "updated_date": datetime.now(timezone.utc),
                "organization_id": visitorlead.get("organization_id"),
                "branch": visitorlead.get("branch"),
                "sender": visitorlead.get("sender")
            }
            }
        result = await visitor_leads.update_one(query, update_fields, upsert=True)
        if result.matched_count > 0:
            print("Document updated successfully.")
            return "200"
        elif result.upserted_id:
            print(f"New document created with ID: {result.upserted_id}")
            return "200"
        else:
            return None
            
        
    except Exception as error:
        print(f"Error updating visitor lead in MongoDB: {error}")
        return None



def confirmation_service(confirmation_url: str, lead_id: str = None):
    try:
        payload = json.dumps({
            "booking_id": lead_id
        })

        headers = {
            "Authorization": authorization_id,
            "Content-Type": "application/json"
        }

        response = requests.request("POST",confirmation_url, headers=headers, data=payload)
        print(response.text)
        return response
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")  
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")  
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  


async def calendar_post_crm_post_task(calendar_contents: dict = {}, mongo_data: dict = {}):
    try:
        if calendar_contents:
            pass
        else:
            mongo_data["event_id"] = None
            mongo_data["cancel_book"] = False

            data_mongo = VisitorLead(**mongo_data)

            lead_id = await create_visitor_lead(data_mongo.model_dump())
            if lead_id:
                print(f"Lead created with ID: {lead_id}")
                confirmation_url = automation_url+"/webhook/create_confirmation"
                response = confirmation_service(confirmation_url=confirmation_url, lead_id=lead_id)
            else:
                print("Failed to create lead in MongoDB")

    except Exception as e:
        print(f"Error in calendar_post_crm_post_task: {e}")



async def Cancel_tour_calendar_post_crm_post_task(calendar_contents: dict = {}, visitor_lead_details: dict = {}, update_fields: dict = {}):
    try:
        if calendar_contents:
            pass
        else:
            lead_id = str(visitor_lead_details['_id'])
            status = await upsert_visitor_leads(visitor_lead_details, update_fields)
            if status == "200":
                print("Lead Succesfully updated in Mongo after reschedule")
            else:
                print("Failed to update lead in MongoDB")
            if lead_id:
                confirmation_url = automation_url+"/webhook/create_confirmation"
                response = confirmation_service(confirmation_url, lead_id)
            else:
                print("No Lead ID")
    except Exception as e:
        print(f"Error in Cancellation in calendar post crm task: {e}")        


async def Reschedule_tour_calendar_post_crm_post_task(visitor_lead_details: dict = {}, delete_update_field: dict = {}, reschedule_update_field: dict = {}):
    try:
        lead_id = str(visitor_lead_details['_id'])
        status = await upsert_visitor_leads(visitor_lead_details, delete_update_field)
        if status == "200":
            print("Lead successfully updated in Mongo before reschedule (cancellation of old tour)")
        else:
            print("Failed to update lead in MongoDB (cancellation of old tour)")
        
        if lead_id:
            confirmation_url = automation_url + "/webhook/create_confirmation"
            response = confirmation_service(confirmation_url, lead_id)
        else:
            print("No lead ID")

        reschedule_status = await upsert_visitor_leads(visitor_lead_details, reschedule_update_field)
        if status == "200":
            print("Lead succesfully updated in Mongo after reschedule")
        else:
            print("Failed to update lead in MongoDB (reschedule of new tour)")
        
        if lead_id:
            confirmation_url = automation_url + "/webhook/create_confirmation"
            response = confirmation_service(confirmation_url, lead_id)
        else:
            print("No lead ID")
        


    except Exception as e:
        print(f"Error in Rescheduling in calendar post crm task: {e}")