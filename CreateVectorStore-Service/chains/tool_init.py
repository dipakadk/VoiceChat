import os
import re
import time
import json
import base64
import uvicorn
import asyncio
import argparse
import requests
import websockets
from twilio.rest import Client
from utils.redis_whatsapp import *
from fastapi import FastAPI, WebSocket
from datetime import datetime,timezone

from langchain_openai import ChatOpenAI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv, find_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain.schema.runnable import RunnableMap
from fastapi.websockets import WebSocketDisconnect
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser


load_dotenv(find_dotenv())

api_key = os.getenv('OPEN_API_KEY')

string_parser = StrOutputParser()
json_parser = JsonOutputParser()


embeddings=OpenAIEmbeddings(api_key=api_key)

llm = ChatOpenAI(api_key=api_key)

today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")





def general_keepme(data):
    query = data.get("query")
    org_id = data.get("clientId")
    branch = data.get("locationId")
    
    
    import requests
    
    similarity_url = os.getenv("BOOKING_URL")
    
    
    url = f"{similarity_url}/llm/vectordb/similarity/search"

    params = {
        "query": query,
        "branch": branch,
        "organization_id":org_id
        }

    response = requests.get(url, params=params)

    response_json = response.json()
    context = response_json.get("similarity")

    
    
    
    print("<><><><><><><><><><><> Inside Book Genneral Keepme Function<><><><><><><><>><><><")
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
            "context": context ,
        }) | template | llm | string_parser
    res = chain.invoke({"query": query})
    return res





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






def book_tool(data:dict):
    print("<><><><><><><><><><><> Inside Book Tool Function<><><><><><><><>><><><")
    print("Query of the user", data.get('query'))
    
    date_final = convert_date_format(query= data.get('query'))
    
    converted_date = date_final.get('converted_date')
    time = date_final.get('time')
    start_time = date_final.get('start_time')
    end_time = date_final.get('end_time')
    
    query = data.get('query', None)
    
    first_name = data.get('first_name', None)
    last_name = data.get('last_name', None)
    Email = data.get('email', None)
    Phonenumber = data.get('phone_number', None)

    locationId = data.get('locationId', None)
    clientId = data.get('clientId', None)
    callId = data.get('branchId', None)
    external_id = f"km{callId}"
    
    # senderId = data.get("senderId", None)




    sender_id = 'abc'
    note = {}
    notes = json.dumps(note)
    params = {
      "startDate": start_time,
      "endDate": end_time,
      "time": time,
      "convertedDate": converted_date,
      
      "firstName": first_name,
      "lastName": last_name,
      "Email": Email,
      "Phonenumber": Phonenumber,
      "clientId": clientId,
      "branchId": locationId,
      "sender": callId,
      "external_id":external_id,
      "note": notes
    }
    
    print(params)
    # query, name= None, date= None, time= None
    final_params = json.dumps(params)
    api_post_booking = "https://llmstaging.keepme.ai/llm/create/booking/visitorleads"
    
    headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
    }   
    import requests
    setData(sender_id, params)
    dump = json.dumps(params)

    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    booking_url = os.getenv('BOOKING_URL')
    api_post_booking = f"{booking_url}/llm/create/booking/visitorleads"
    
    response = requests.post(api_post_booking, data=dump, headers= headers)    
    
    status_code = f"Status Code {response.status_code}"
    response_body = f"Response Body: {response.json()}"
    response = f"{status_code}, {response_body}" 
    
    return f"Booking Status - {response}"
    
    
def reschedule_tool(data:dict):
    print()
    print()
    print("<><><><><><><><><><><> Inside Reschedule Tool Function<><><><><><><><>><><><")
    print()
    query = data.get('query', None)
    first_name = data.get('first_name', None)
    last_name = data.get('last_name', None)
    Email = data.get('email', None)
    Phonenumber = data.get('phone_number', None)
    start_date = data.get('date', None)
    time = data.get('time', None)
    end_date = f"{start_date} + 1 hour"
    clientId = data.get('clientId', None)
    locationId = data.get('locationId', None)
    callId = data.get('branchId', None)
    # senderId = data.get("senderId", None)
    external_id = f"km{callId}"
    
    if query is not None and date is not None and date is not None and time is not None:
        start_date_final = convert_date_format(query)
        sender_id = 'abc'
    
    params = {
      "startDate": start_date_final,
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
      "external_id":external_id
    }
    "llm/create/booking/visitorleads"
    if getData(callId):
        a = getData(callId)
        a['startDate'] = start_date_final
        a['endDate'] = end_date
        a['time'] = time
        setData(sender_id, a)
        return "Your booking has been rescheduled"
    else:
        return "No booking found- From Reschedule"
    
def cancel_tool(data):
    """Cancel booking tool"""
    print(data)
    print("<><><><><><><><><><><> Inside Cancel Tool Function<><><><><><><><>><><><")
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