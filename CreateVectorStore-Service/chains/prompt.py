from datetime import datetime,timezone
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()
llm = ChatOpenAI(api_key=os.getenv('OPEN_API_KEY'))
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate
import json
output_parser = StrOutputParser()
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser()
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import json
import base64
import asyncio
import argparse
import time
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
import re
from langchain_openai import OpenAIEmbeddings
load_dotenv()

from langchain.schema.runnable import RunnableMap
from langchain_core.output_parsers import StrOutputParser
string_parser= StrOutputParser()
import os
api_key = os.getenv('OPEN_API_KEY')
from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate
embeddings=OpenAIEmbeddings(api_key=api_key)

llm = ChatOpenAI(api_key=os.getenv('OPEN_API_KEY'))


from datetime import datetime,timezone


today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")


today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")



def general_keepme(query):

    prompt = """You are given a context and a query. Answer the query based on the context provided to you.
      ##query:`{query}`
      ##context: 'answer them we do not know answer'.
      Give detailed answers when necessary, but avoid providing any information not included in the context.
      Be concise with your response, just answer what is asked in the query, be conversational as much as possible.
      dont respond with the word such as 'not provided in the context'
      only answer what is specifically asked in the query,dont answer everything from the context.

      <Response>
      - Try to always keep the answer short and sweet. Do not EVER PROVIDE UNNECESSARY RESPONSE of what is not asked in the query.
      - Your response should always be in markdown format.
      </Response>
      """
      
    template= ChatPromptTemplate.from_template(template=prompt)
    chain = RunnableMap({
            'query': lambda x: x['query'],
        }) | template | llm | string_parser
    res = chain.invoke({"query": query})
    return res


from datetime import datetime



def convert_date_format(query:str):
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
        
        prompt_and_model = prompt | llm | json_parser
        output =  prompt_and_model.invoke({"query": query,"today":date, "day":day_of_week})
        return output





from utils.redis_whatsapp import *
def book_tool(data:dict):
    query = data.get('query', None)
    first_name = data.get('name', None)
    last_name = data.get('name', None)
    Email = data.get('email', None)
    Phonenumber = data.get('phone_number', None)
    start_date = data.get('date', None)
    time = data.get('time', None)
    end_date = f"{start_date} + 1 hour"
    clientId = data.get('clientId', None)
    locationId = data.get('branchId', None)
    callId = data.get('branchId', None)
    
    
    params = {
      "startDate": date,
      "firstName": first_name,
      "lastName": last_name,
      "Email": Email,
      "Phonenumber": Phonenumber,
      "time": time,
      "endDate": end_date,
      "convertedDate": "convertedDate",
      "clientId": clientId,
      "branchId": locationId,
      "sender": callId,
    }
    # query, name= None, date= None, time= None
    if query is not None and date is not None and date is not None and time is not None:
        date_final = convert_date_format(query)
        sender_id = 'abc'
       
        setData(sender_id, params)
        return "Your booking has been confirmed"
    
    
def reschedule_tool(data:dict):
    print()
    print()
    print()
    query = data.get('query', None)
    name = data.get('name', None)
    date = data.get('date', None)
    time = data.get('time', None)
    sender_id = 'abc'
    
    if getData(sender_id):
        a = getData(sender_id)
        a['name'] = name
        a['date'] = date
        a['time'] = time
        setData(sender_id, a)
        return "Your booking has been rescheduled"
    else:
        return "No booking found- From Reschedule"
    
def cancel_tool(data):
    """Cancel booking tool"""
    print(data)
    sender_id = 'abc'
    print()    
    print("---------------------------")    
    print("Cancel Tool")    
    print()    
    print()    
    if getData(sender_id):
        deleteData(sender_id)
        return "Your booking has been cancelled"
    else: 
        return "No booking found to cancel it."