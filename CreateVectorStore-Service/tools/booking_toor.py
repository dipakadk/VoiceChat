
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate
import json
# from services.send_email import sendCalanderEvents
# from services.twilio_service import send_whatsapp_message
from services.visitor_create_db import  upsert_visitor
# from services.http_api import http_post
from db.visitors import Visitor, Session_by_email_phone

output_parser = StrOutputParser()
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser()
from datetime import datetime,timezone,timedelta
from utils.utils import extract_message #, post_event_to_crm
# from db.vector_store import VisitorLead
# from db.db_config import visitor_leads
from services.backgroundService import calendar_post_crm_post_task
from services.http_api import calculate_time_seconds
from utils.redis_whatsapp import setData
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
COUNTRY_CODE = os.getenv("COUNTRY_CODE")
SEND_CONFIRMATION_URL=os.getenv("SEND_CONFIRMATION_URL")
import pytz


def format_phone_number(phone_number=None, branch_details=None, agent=None):
    country_code = branch_details.get("countryCode") if branch_details else None
    if phone_number.startswith("+"):
        formatted_phone = phone_number
    else:
        if agent in ["Whatsapp","whatsapp","sms"]:
             formatted_phone=f"+{phone_number}"
        else:
            formatted_phone = f"{country_code}{phone_number}" if country_code else f"{phone_number}"
    return formatted_phone
             



async def booking_user_form_tool(self):
    
    async def booking_user_form_chain_tool(**data):
        try: 
            print(data,"=============tool booking data=========================")
            date=data.get('date')
            time=data.get('time')
            firstname=data.get('firstname')
            lastname=data.get('lastname')
            email=data.get('email')
            phonenumber=data.get('phonenumber')
            visit_type = data.get("visit_type")
            
            json_date = await convert_date_format(date+time)
            startime = json_date.get("start_time")
            endtime = json_date.get("end_time")
            print("Sender in booking tool===========",self.sender)
            if not firstname:
                 return "Please provide your first name"
            if not lastname:
                 return "Please provide your lastname"
            if not email:
                 return "Please provide your email address"
            if not phonenumber:
                 return "Please provide your Phone number"
            if firstname and lastname and email and phonenumber and startime and endtime:
                    print(json_date)
                    phonenumber =f"{format_phone_number(phonenumber,self.client_details,self.agent)}"
                    
                    # 
                    messages=self.history.messages
                    extracted_history=await extract_message(messages,self.welcome_message)
                    extracted_history=extracted_history.get("note")

                    tz = timezone.utc
                    if self.client_details.get("timezone"):
                        try:
                            tz = pytz.timezone(self.client_details.get("timezone"))
                        except Exception as e:
                            tz = timezone.utc
                    
                    self.tourBooked = True

                    if self.welcome_message:
                        
                        extracted_history += f"<p>Human: {self.query}</p><p>AI: That's booked. Confirmations are on the way to you.</p>"
                    else:    
                        extracted_history += f"<p>Human: {self.query}</p><p>AI: That's booked. Confirmations are on the way to you.</p>"

                    total_seconds = await calculate_time_seconds(start_time_str=startime, tz_str=self.client_details.get("timezone") or "UTC")
                    
                    mongo_crm_data={
                            "start_date":startime,
                            "time":json_date.get("time") or time,
                            "email":email,
                            "end_date":endtime,
                            "converted_date":json_date.get("converted_date") or None,
                            "venue_name":self.client_details.get('branch_name') or None,
                            "first_name":firstname ,
                            "last_name":lastname ,
                            "phone":phonenumber,    
                            "source_group":self.agent or "web",
                            "source_name": "AI Agent",
                            "type": (str(visit_type).capitalize() if visit_type else "Tour"),
                            "salesperson": "James Smith",
                            "interested_in": "Fitness, Personal Training",
                            "form_name": "Visitor Free Class Form",
                            "organization_id":self.org_id,
                            "branch":self.branch,
                            "created_date": datetime.now(timezone.utc),
                            "updated_date": datetime.now(timezone.utc),
                            "sender":self.sender,
                            "venue_id":self.venue_id or None,
                            "confirm_book":True,
                            "note": extracted_history,
                            "external_id": f"km{self.sender}",
                            "expire_time": datetime.now(tz) + timedelta(seconds=total_seconds)
                    } 
                    self.tourBooked = True
                    
                    setData(f"{self.history_sender_branch}_booked", "True",total_seconds)
                    setData(f"{self.history_sender_branch}_booked_slot",str(json_date.get("converted_date"))+" "+str(json_date.get("time")),total_seconds)

                    if self.agent not in ["whatsapp", "email", "sms"]:
                        phone_key_base = f"{self.sender}_{self.org_id}_{self.branch}"
                        
                        setData(f"{phone_key_base}_booked", "True", total_seconds)
                        setData(f"{phone_key_base}_booked_slot", f"{json_date.get('converted_date')} {json_date.get('time')}", total_seconds)

                   
                    


                    # s1 = Session_by_email_phone(
                    #      email=email,
                    #      phone=phonenumber.replace("+",""),
                    #      active_session_id=self.sender,
                    #      region_id=self.region_id,
                    #      branch=self.branch,
                    #      whatsapp_number=self.whatsapp_number,
                    #      organization_email=self.organization_email,
                    #      organization_id=self.org_id,
                    #      expires_at=datetime.now(tz) + timedelta(seconds=total_seconds),
                    #      created_date=datetime.now(timezone.utc)
                    # )

                    # self.background_tasks.add_task(upsert_session,s1)
                    
                    
                    
                    visitor_data = Visitor(
                        updated_date= datetime.now(timezone.utc),
                        created_date= datetime.now(timezone.utc),
                        sender=self.sender,
                        organization_id=self.org_id,
                        agent=[self.agent or "web"],
                        region_id = self.region_id,
                        details={
                            "first_name":firstname,
                            "last_name":lastname,
                            "phone_number":phonenumber,
                            "email_address":email
                        }
                    )
                    self.background_tasks.add_task(upsert_visitor, visitor_data)

                    
                    try:    
                            
                            self.background_tasks.add_task(calendar_post_crm_post_task, {}, mongo_crm_data)
                            print("Booking Lead successfully posted in CRM")
                            
                            return "Booking successful"

                    except Exception as e:
                        print(e,"===============================booking error==========")
                        print("\n\n","Booking Lead post in CRM Failed","\n\n")

        except json.JSONDecodeError:
                print("Invalid JSON format.")
                
    
    async def convert_date_format(query:str):
        prompt = ChatPromptTemplate.from_template(
            template = """
         You only speak in json. You are provided with the following inputs:
            User query: Contains a date and time in double backticks:
            query: ``{query}``
            Today's date: Provided in single backticks:
            today: `{today}`
            Today's day: Provided in triple backticks:
            day: ```{day}```
            Your task:
            Interpret the user's query to extract the required date and time.
            Analyze the given date (today) and day (day) to ensure the selected date and time are valid and do not refer to the past.
            Use the current year if the query does not explicitly specify one. Even if the query consist of past years and months (For example:2023),Be precise on finding out the future time the user wants to book on.
            Respond in JSON format without extra tags, backticks, or phrases. The json response should include:
            dict(
            "converted_date": "The final interpreted date in YYYY-MM-DD, Dayname format."
            "time": "The extracted or inferred time in hh:mm AM/PM format."
            "start_time": "The start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."
            "end_time": "The end time, one hour after the start time, in ISO 8601 format."
            )
            Reminder that dict refers to curly brackets.
            If the query includes relative terms like "Today" or "Tomorrow," calculate the date and time accordingly based on today and day. Ensure no selection is made for past dates or times.
            """
        )
        tz = timezone.utc
        if self.client_details.get("timezone"):
            try:
                tz = pytz.timezone(self.client_details.get("timezone"))
            except Exception as e:
                tz = timezone.utc
            
        today_date = datetime.now(tz)
            

        day_of_week = today_date.strftime("%A")
        date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")
        prompt_and_model = prompt | self.llm | json_parser
        output = await prompt_and_model.ainvoke({"query": query,"today":date, "day":day_of_week})
        return output

    return booking_user_form_chain_tool


        

######################## Comments Unused Codes############################################################ 

# whatsapp_data={
                    #         "first_name":firstname,
                    #         "last_name":lastname,
                    #         "phone_number":phonenumber.replace("+",""),
                    #         "sender":self.sender,
                    #         "email_address":email,
                    #         "start_time":startime,
                    #         "agent":self.agent or "web",
                    #         "end_time":endtime,
                    #         "date":json_date.get("converted_date") or date,
                    #         "time": json_date.get("time") or time,
                    #         "organization_id":self.org_id,
                    #         "branch":self.branch,
                    #         "message":f"Thank you for scheduling a tour of {self.client_details.get('branch_name') or None}",
                    #         "location":self.client_details.get("branch_address") or None,
                    #         "description":"Book a tour",
                    # }
                    # print(whatsapp_data)
                    # calander_data={
                    #         "first_name":firstname,
                    #         "last_name":lastname,
                    #         "date":json_date.get("converted_date") or date,
                    #         "time":json_date.get("time") or time,
                    #         "startTime":startime,
                    #         "emailAddress":email,
                    #         "endTime":endtime,
                    #         "summary":f"Book a tour ({firstname})",
                    #         "description":"Book a tour",
                    #         # "attendees":[email],
                    #         "location":self.client_details.get("branch_address") or "71-75 Shelton Street Covent Garden, London",
                    #         "sender":self.sender,
                    # }


# crm_data={
                    #         "start_date":startime,
                    #         "email":email,
                    #         "end_date":endtime,
                    #         "venue_name":self.client_details.get('branch_name') or None,
                    #         "first_name":firstname ,
                    #         "last_name":lastname ,
                    #         "phone":phonenumber,
                    #         "source_group":self.agent or "web",
                    #         "source_name": "AI Agent",
                    #         "type": (str(visit_type).capitalize() if visit_type else "Tour"),
                    #         "salesperson": "James Smith",
                    #         "gender": "male or female or undefined",
                    #         "city": "string",
                    #         "state": "string",
                    #         "zip": "string",
                    #         "dob": "date",
                    #         "interested_in": "Fitness, Personal Training",
                    #         "referred_by": "Friend",
                    #         "form_name": "Visitor Free Class Form",
                    #         "sender":self.sender,
                    #         "venue_id":self.venue_id or None
                    # } 


                    # calander_url=f"{self.calander_api_url}/events?calendar={self.calander_name}&id={self.calanderid_book_tour}"
 # headers={'Content-Type': 'application/json',"api-key":self.calander_api_key}
                    # calendar_dict = {
                    #     "headers":headers,
                    #     "calendar_url":calander_url,
                    #     "calendar_data":calander_data
                    # }
                    # self.background_tasks.add_task(send_whatsapp_message, whatsapp_data)
                            # self.background_tasks.add_task(sendCalanderEvents, calander_data)
                            # self.background_tasks.add_task(http_post, url=SEND_CONFIRMATION_URL, headers=headers, data=whatsapp_data)
                            
                            # self.background_tasks.add_task(http_post, url=calander_url, headers=headers, data=calander_data)
                            #self.background_tasks.add_task(http_post, url=f'{self.crm_api_url}/h7KpT3fDqRvJbZx', headers=headers, data=crm_data)
#create visitor details with email,phone number and session_id in mongodb
                            
                            # self.background_tasks.add_task(create_visitors_session, whatsapp_data)

                            
                            #check is visitor is new and recently posted leads in crm and post all previous history of that session
                            
                                
                                #self.background_tasks.add_task(post_event_to_crm, self, extracted_history, identifier)
