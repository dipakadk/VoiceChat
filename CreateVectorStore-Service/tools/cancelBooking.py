from langchain_core.output_parsers import StrOutputParser
from services.http_api import http_delete
from langchain_core.prompts import ChatPromptTemplate
from services.visitor_create_db import  upsert_visitor_leads, get_visitor_lead_details,upsert_session
from datetime import datetime, timezone, timedelta
from utils.redis_whatsapp import setData
from services.backgroundService import Cancel_tour_calendar_post_crm_post_task
import pytz
from db.visitors import Session_by_email_phone

from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

SESSION_EXPIRE_TIME = os.getenv("SESSION_EXPIRE_TIME") or 7200


async def CancelBooking(self):
    async def cancel_tour(query:str):
        try:
            visitor_details= await get_visitor_lead_details(self.sender,self.org_id,self.branch)
            print("Details is=================",visitor_details)
            confirmBook = None
            if visitor_details is not None:
                confirmBook = visitor_details.get("confirm_book",None)
            if confirmBook in [False, None]:
                template = """
                    The user is trying to cancel his/her booked tour/trial appointment.
                    However it has been known that the user in the past has not booked any tour appointment.
                    Your task is to create a simple message stating that You have not booked any tour before to cancel it.
                    Make it human like and polite response.
                    Do not add any additional texts in your response.
                    {input}
                """
                cancel_prompt = ChatPromptTemplate.from_template(template=template) 
                chain = cancel_prompt | self.llm | StrOutputParser()
                return await chain.ainvoke({"input": ""})
            else:
                try:
                    formatted_date = visitor_details.get("converted_date")

                    self.tourBooked = True

                    tz = timezone.utc
                    if self.client_details.get("timezone"):
                        try:
                            tz = pytz.timezone(self.client_details.get("timezone"))
                        except Exception as e:
                            tz = timezone.utc
                   
                    update_fields = {
                        "cancel_book": True,
                        "confirm_book": False,
                        "expire_time": datetime.now(tz) + timedelta(seconds=int(SESSION_EXPIRE_TIME))
                    }
                    self.tourBooked = True

                    tz = timezone.utc
                    if self.client_details.get("timezone"):
                        try:
                            tz = pytz.timezone(self.client_details.get("timezone"))
                        except Exception as e:
                            tz = timezone.utc
                    
                    self.tourBooked = True

                    # s1 = Session_by_email_phone(
                    #      email=visitor_details.get("email"),
                    #      phone=visitor_details.get("phone"),
                    #      active_session_id=self.sender,
                    #      region_id=self.region_id,
                    #      branch=self.branch,
                    #      whatsapp_number=self.whatsapp_number,
                    #      organization_email=self.organization_email,
                    #      organization_id=self.org_id,
                    #      expires_at=datetime.now(tz) + timedelta(seconds=7200),
                    #      created_date=datetime.now(timezone.utc)
                    # )
                    # self.background_tasks.add_task(upsert_session,s1)

                    self.background_tasks.add_task(Cancel_tour_calendar_post_crm_post_task,calendar_contents={},visitor_lead_details= visitor_details,update_fields=update_fields)
                    setData(f"{self.history_sender_branch}_booked",None)
                    setData(f"{self.history_sender_branch}__booked_slot",None)
                    
                    if self.agent not in ["whatsapp", "email", "sms"]:
                        phone_key_base = f"{self.sender}_{self.org_id}_{self.branch}"
                            
                        setData(f"{phone_key_base}_booked", None)
                        setData(f"{phone_key_base}_booked_slot", None)


                    return f"Tour Booking Cancellation Successful for {formatted_date}"
                except Exception as error:
                    print("\n\n","Booking Lead post for Cancellation in CRM Failed","\n\n",error) 
        except Exception as error:
            print("Error========",error)
            return None

    return cancel_tour




#### Unused code comments

 # calander_url=f"{self.calander_api_url}/events/{eventID}?calendar={self.calander_name}&id={self.calanderid_book_tour}"
                    # headers={'Content-Type': 'application/json',"api-key":self.calander_api_key} 
                    # self.background_tasks.add_task(http_delete, calander_url, headers)