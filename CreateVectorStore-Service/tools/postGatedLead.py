from db.visitors import Visitor
from datetime import datetime, timezone
from services.visitor_create_db import upsert_visitor
from fastapi import HTTPException
from services.http_api import http_post
from utils.utils import post_event_to_crm, extract_message

def format_phone_number(phone_number=None, branch_details=None, agent=None):
    country_code = branch_details.get("countryCode") if branch_details else None
    if phone_number.startswith("+"):
        formatted_phone = phone_number
    else:
        if agent in ["Whatsapp","whatsapp","sms"]:
             formatted_phone=f"+{phone_number}"
        else:
            formatted_phone = f"+{country_code}{phone_number}" if country_code else f"{phone_number}"
    return formatted_phone
             

async def PostLeadGated(self):
    async def post_lead(firstname:str, lastname:str, email:str, phonenumber:str):
        if firstname and lastname and email and phonenumber:
            phonenumber =f"{format_phone_number(phonenumber,self.client_details,self.agent)}"
            visitor_data = Visitor(
                            updated_date= datetime.now(timezone.utc),
                            created_date= datetime.now(timezone.utc),
                            sender=self.sender,
                            organization_id=self.org_id,
                            agent=[self.agent or "web"],
                            details={
                                "first_name":firstname,
                                "last_name":lastname,
                                "phone_number":phonenumber,
                                "email_address":email
                            }
            )
            # crm_data={
            #                 "start_date":None,
            #                 "email":email,
            #                 "end_date":None,
            #                 "venue_name":self.client_details.get('branch_name') or 'Keepme Fit Club',
            #                 "first_name":firstname ,
            #                 "last_name":lastname ,
            #                 "phone":phonenumber,
            #                 "source_group":self.agent or "web",
            #                 "source_name": "AI Agent",
            #                 "type":None,
            #                 "salesperson": "James Smith",
            #                 "gender": "male or female or undefined",
            #                 "city": "string",
            #                 "state": "string",
            #                 "zip": "string",
            #                 "dob": "date",
            #                 "interested_in": "Fitness, Personal Training",
            #                 "referred_by": "Friend",
            #                 "form_name": "Visitor Free Class Form",
            #                 "sender":self.sender,
            #                 "venue_id":self.venue_id or None
            # }
            # headers={'Content-Type': 'application/json',"api-key":self.calander_api_key}

            try:
                self.background_tasks.add_task(upsert_visitor, visitor_data)
                # self.background_tasks.add_task(http_post, url=f'{self.crm_api_url}/h7KpT3fDqRvJbZx', headers=headers, data=crm_data)
                # if self.isVistor_new:
                #     messages=self.history.messages
                #     print("message============",messages)
                #     extracted_history=extract_message(messages)
                #     print("message============",extracted_history)
                #     extracted_history=extracted_history.get("note")
                #     identifier=email if email else phonenumber
                #     self.background_tasks.add_task(post_event_to_crm, self, extracted_history, identifier)
            
                return "Lead POST Successful"
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))



    return post_lead