from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap
from datetime import datetime, timezone
import pytz

async def GetAvailableTimeSlot(database, llm):
    template = """
        You are provided with the context inside double backticks that contains the booking time slot of the club.
        Ignore the operating hours and staffed hours if available in the context. Only look for the data specified as "Booking Slots".
        Context is : ``{context}``
        Your task is to provide a response stating what the available booking time slots of the club are.
        Do not add any additional backticks or texts in your response.
        Just state what the available time slots are.
    """
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    contexts = [k.page_content for k in database.similarity_search("booking slot",k=4)]
    print("Contexts===============",contexts)
    return await chain.ainvoke({"context": contexts})


async def checkTime(self):
    async def check_available_timeslot(query:str, time_slots:str):
        
        if time_slots in ["None", None, "null", "", " "]:
            time_slots = await GetAvailableTimeSlot(self.branch_database, self.llm)
        

        print("time slots are==========================",time_slots)
        template = """
            You are provided with a user query attempting to book a tour, trial, or pass with the date (and possibly time) specified within double backticks: ``{query}``. 
           
           You are also provided with the available time slots for booking for a club inside triple backticks: ```{available}```. 
           
           Use the current weekday `{Day}`, today's date `{Today}`, and the current time `{Time}` to validate the request.
            Ensure the provided date is valid: it must be within the up-coming next 30 days from `{Today}` and `{Time}` and **cannot be in the past**. Accept and interpret relative inputs like "today," "tomorrow", "Day after tomorrow", or "this Sunday," converting them into specific dates for validation. 
            
            For time validation, check that the selected date is not in the past and, if it is today, ensure the time is later than `{Time}`.
            
            Cross-reference the user's selected date and time with the available slots; if no time is mentioned, provide available slots for that day. 
            
            If the date is invalid, respond: "That date is unavailable. Could you please book for some another date?" If the time or day is invalid, prompt: "The selected time is not available. Could you choose another time?" or "Bookings are not available on `{Day}`. 
            Could you pick another day?" 
            
            If all criteria are met and time is specified, confirm: "The requested date and time .... is available for booking. Shall we begin the process?" 
            
            If criteria are met but the user has not selected a time, respond: "Great! What time suits you? We have slots available from {available}." 
            
            Always ensure the logic excludes past dates and times, and focus only on valid future bookings within the 30-day limit.
             """
        tz = timezone.utc
        if self.client_details.get("timezone"):
            try:
                tz = pytz.timezone(self.client_details.get("timezone"))
            except Exception as e:
                tz = timezone.utc
            
        current_utc = datetime.now(tz)
        formatted_date = current_utc.strftime("%A, %B %d, %Y")
        # formatted_time = current_utc.strftime("%H:%M %p")
        formatted_time_24 = current_utc.strftime("%H:%M %p")
        formatted_time_12 = current_utc.strftime("%I:%M %p")
        formatted_day = current_utc.strftime("%A")
        formatted_time = f"[{formatted_time_24} ({formatted_time_12})]"
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        return await chain.ainvoke({"query": query, "available": time_slots, "Today": formatted_date, "Time":formatted_time, "Day":formatted_day})
    return check_available_timeslot


