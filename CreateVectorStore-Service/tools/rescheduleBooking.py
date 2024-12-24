from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from services.visitor_create_db import  upsert_visitor_leads, get_visitor_lead_details,upsert_session
from langchain_core.runnables import RunnableMap
# from services.http_api import http_delete, http_post
from datetime import datetime, timezone,timedelta
# from services.send_email import sendCalanderEvents
# from services.twilio_service import send_whatsapp_message
from services.backgroundService import Reschedule_tour_calendar_post_crm_post_task
from utils.redis_whatsapp import setData
from services.http_api import calculate_time_seconds
import pytz
from db.visitors import Session_by_email_phone

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os

SESSION_EXPIRE_TIME = os.getenv("SESSION_EXPIRE_TIME") or 7200

async def RescheduleBooking(self):
    async def reschedule_booking(date:str, time:str):
        visitor_details= await get_visitor_lead_details(self.sender,self.org_id,self.branch)
        print("Details is=================",visitor_details)
        confirmBook = None
        if visitor_details is not None:
            confirmBook = visitor_details.get("confirm_book",None)
        if confirmBook in [False, None]:
            template = """
                The user is trying to reschedule his/her booked tour/trial appointment.
                However it has been known that the user in the past has not booked any tour appointment.
                Here is the date and time the user is trying to reschedule its tour appointment to: Date is {date} and time is {time}.
                Create a Human like and friendly response stating that you have not booked any appointments, Would you like to book a tour instead?
            """
            prompt = ChatPromptTemplate.from_template(template=template)
            chain = RunnableMap({"date": lambda x: x["date"], "time":lambda x: x["time"]})| prompt | self.llm | StrOutputParser()
            return chain.invoke({"date": date, "time": time})
        else:
            try:


                json_date = await convert_date_format(str(date+time))
                startime = json_date.get("start_time")
                endtime = json_date.get("end_time")

                
                total_seconds =await calculate_time_seconds(start_time_str=startime, tz_str=self.client_details.get("timezone") or "UTC")
                setData(f"{self.history_sender_branch}_booked", "True",total_seconds)
                setData(f"{self.history_sender_branch}_booked_slot",str(json_date.get("converted_date"))+" "+str(json_date.get("time")),total_seconds)

                if self.agent not in ["whatsapp", "email", "sms"]:
                    phone_key_base = f"{self.sender}_{self.org_id}_{self.branch}"
                        
                    setData(f"{phone_key_base}_booked", "True", total_seconds)
                    setData(f"{phone_key_base}_booked_slot", f"{json_date.get('converted_date')} {json_date.get('time')}", total_seconds)
                


                tz = timezone.utc
                if self.client_details.get("timezone"):
                    try:
                        tz = pytz.timezone(self.client_details.get("timezone"))
                    except Exception as e:
                        tz = timezone.utc
                
                self.tourBooked = True

                # s1 = Session_by_email_phone(
                #          email=visitor_details.get("email"),
                #          phone=visitor_details.get("phone"),
                #          active_session_id=self.sender,
                #          region_id=self.region_id,
                #          branch=self.branch,
                #          whatsapp_number=self.whatsapp_number,
                #          organization_email=self.organization_email,
                #          organization_id=self.org_id,
                #          expires_at=datetime.now(tz) + timedelta(seconds=total_seconds),
                #          created_date=datetime.now(timezone.utc)
                # )

                # self.background_tasks.add_task(upsert_session,s1)
                

                old_update_field = {
                   "cancel_book": True,
                    "confirm_book": False,
                    "expire_time": datetime.now(tz) + timedelta(seconds=int(SESSION_EXPIRE_TIME))
                }

                new_update_fields = {
                    "start_date": startime,
                    "end_date": endtime,
                    "converted_date": json_date.get("converted_date") or None,
                    "time": json_date.get("time") or time,
                    "cancel_book": False,
                    "confirm_book": True,
                    "expire_time": datetime.now(tz) + timedelta(seconds=total_seconds)
                }

                self.background_tasks.add_task(Reschedule_tour_calendar_post_crm_post_task,visitor_lead_details=visitor_details, delete_update_field=old_update_field, reschedule_update_field=new_update_fields)                
                return f"Rescheduling successful for {time}"


            except Exception as error:
                print("Error occured....",error)






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
        self.tourBooked = True
        tz = timezone.utc
        if self.client_details.get("timezone"):
            try:
                tz = pytz.timezone(self.client_details.get("timezone"))
            except Exception as e:
                tz = timezone.utc
            
        today_date = datetime.now(tz)
            

        day_of_week = today_date.strftime("%A")
        date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")
        prompt_and_model = prompt | self.llm | JsonOutputParser()
        output = await prompt_and_model.ainvoke({"query": query,"today":date, "day":day_of_week})
        return output


    return reschedule_booking



##### Unused code Comments ######################

            ## Cancel Current Booked Events first
                # cancel_calander_url=f"{self.calander_api_url}/events/{eventID}?calendar={self.calander_name}&id={self.calanderid_book_tour}"

                # self.background_tasks.add_task(http_delete, cancel_calander_url, headers)


                # whatsapp_data={
                #                 "first_name":self.metadata.get("first_name"),
                #                 "last_name":self.metadata.get("last_name"),
                #                 "phone_number":self.metadata.get("phone_number"),
                #                 "sender":self.sender,
                #                 "email_address":self.metadata.get("email_address"),
                #                 "start_time":startime,
                #                 "agent":self.agent or "web",
                #                 "end_time":endtime,
                #                 "date":json_date.get("converted_date") or date,
                #                 "time": json_date.get("time") or time,
                #                 "organization_id":self.org_id,
                #                 "branch":self.branch,
                #                 "message":"Thank you for rescheduling a tour of Keepme Fit Club!",
                #                 "location":"71-75 Shelton Street Covent Garden, London",
                #                 "description":"Reschedule booked tour",
                # }
                # calander_data={
                #                 "first_name":self.metadata.get("first_name"),
                #                 "last_name":self.metadata.get("last_name"),
                #                 "date":json_date.get("converted_date") or date,
                #                 "time":json_date.get("time") or time,
                #                 "startTime":startime,
                #                 "emailAddress":self.metadata.get("email_address"),
                #                 "endtime":endtime,
                #                 "summary":f"Reschedule a tour ({self.metadata.get('first_name')})",
                #                 "description":"Reschedule a tour",
                #                 # "attendees":[email],
                #                 "location":"71-75 Shelton Street Covent Garden, London",
                #                 "sender":self.sender,
                # }
                # crm_data={
                #                 "start_date":startime,
                #                 "email":self.metadata.get("email_address"),
                #                 "end_date":endtime,
                #                 "venue_name":"Keepme Fit Club",
                #                 "first_name":self.metadata.get("first_name"),
                #                 "last_name":self.metadata.get("last_name"),
                #                 "phone":self.metadata.get("phone_number"),
                #                 "source_group":self.agent or "web",
                #                 "source_name": "AI Agent",
                #                 "type": "Tour",
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
                #         } 
                

                # self.background_tasks.add_task(send_whatsapp_message, whatsapp_data)
                # self.background_tasks.add_task(sendCalanderEvents, calander_data)
                # self.background_tasks.add_task(http_post, url=SEND_CONFIRMATION_URL, headers=headers, data=whatsapp_data)
                # self.background_tasks.add_task(http_post, url=f'{self.crm_api_url}/h7KpT3fDqRvJbZx', headers=headers, data=crm_data)


# calander_url=f"{self.calander_api_url}/events?calendar={self.calander_name}&id={self.calanderid_book_tour}"
                # calendar_dict = {
                #         "headers":headers,
                #         "calendar_url":calander_url,
                #         "calendar_data":calander_data
                # }


                # headers={'Content-Type': 'application/json',"api-key":self.calander_api_key} 
