# import os
# import json
# import base64
# import asyncio
# import argparse
# import time
# from fastapi import FastAPI, WebSocket
# from fastapi.responses import JSONResponse
# from fastapi.websockets import WebSocketDisconnect
# from twilio.rest import Client
# import websockets
# from dotenv import load_dotenv
# import uvicorn
# from tools.setup_tool import *
# from datetime import datetime

# name = "Ajeet Acharya"

# today_date = datetime.now()
# day_of_week = today_date.strftime("%A")
# date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")
# today = date
# import re
# from langchain_community.embeddings import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma
# load_dotenv()

# from langchain.schema.runnable import RunnableMap
# from langchain_core.output_parsers import StrOutputParser
# string_parser= StrOutputParser()

# import os
# api_key = os.getenv('OPEN_API_KEY')
# from langchain_openai import ChatOpenAI

# # from tools import convert_date_format, general_tool

# from langchain_core.prompts import ChatPromptTemplate
# llm = ChatOpenAI(api_key=os.getenv('OPEN_API_KEY'))
# from langchain_community.embeddings import OpenAIEmbeddings
# embeddings=OpenAIEmbeddings(api_key=api_key)


# # Configuration
# TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
# TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
# PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
# OPENAI_API_KEY = os.getenv('OPEN_API_KEY')
# raw_domain = os.getenv('DOMAIN', '')
# DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) 




# from chains.prompt import system_prompt, tools_last

# VOICE = 'alloy'


# LOG_EVENT_TYPES = [
#     'error', 'response.content.done', 'rate_limits.updated', 'response.done',
#     'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
#     'input_audio_buffer.speech_started', 'session.created'
# ]


# app = FastAPI()

# if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
#     raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# # Initialize Twilio client
# client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# import base64

    
        
# async def send_initial_conversation_item(openai_ws):
#     """Send initial conversation so AI talks first."""
#     initial_conversation_item = {
#         "type": "conversation.item.create",
#         "item": {
#             "type": "message",
#             "role": "user",
#             "content": [
#                 {
#                     "type": "input_text",
#                     "text": (
#                         f"Greet the user with hi, hello, or any other greeting without using any tools. with their name: {name}"
        
#                     )
#                 }
#             ]
#         }
#     }



#     await openai_ws.send(json.dumps(initial_conversation_item))
#     await openai_ws.send(json.dumps({"type": "response.create"}))





# async def initialize_session(openai_ws):
#     global tools_last

#     global system_prompt
#     SYSTEM_MESSAGE = system_prompt 
    
#     print()
#     print()
#     print()
#     print()
#     print()
#     print()
#     print()
#     print("System prompt is ",system_prompt)
#     print()
#     print()
#     print()
#     print()
#     print()
#     print()
#     print(print)
    

#     """Control initial session with OpenAI."""
#     session_update = {
#         "type": "session.update",
#         "session": {
#             "turn_detection": {"type": "server_vad"},
#             "input_audio_format": "g711_ulaw",
#             "output_audio_format": "g711_ulaw",
#             "voice": VOICE,
#             "instructions": SYSTEM_MESSAGE,
#             "modalities": ["text", "audio"],
#             "temperature": 0.9,
#             # Deepak Digamber
#             "tools": tools_last,
#             "tool_choice": "auto",

#         }
#     }
#     print('Sending session update:', json.dumps(session_update))
#     await openai_ws.send(json.dumps(session_update))

#     # Have the AI speak first
#     await send_initial_conversation_item(openai_ws)
    


# async def make_call(phone_number_to_call: str):
#     """Make an outbound call."""
#     # if not phone_number_to_call:
#     #     raise ValueError("Please provide a phone number to call.")

#     # is_allowed = await check_number_allowed(phone_number_to_call)
#     # if not is_allowed:
#     #     raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

#     # # Ensure compliance with applicable laws and regulations
#     # All of the rules of TCPA apply even if a call is made by AI.
#     # Do your own diligence for compliance.

#     outbound_twiml = (
#         f'<?xml version="1.0" encoding="UTF-8"?>'
#         f'<Response><Connect><Stream url="wss://4811-111-119-49-232.ngrok-free.app/llm/media-stream" /></Connect></Response>'
#     )

#     call = client.calls.create(
#         from_=PHONE_NUMBER_FROM,
#         to=phone_number_to_call,
#         twiml=outbound_twiml
#     )

#     await log_call_sid(call.sid)
    

# async def log_call_sid(call_sid):
#     """Log the call SID."""
#     print(f"Call started with SID: {call_sid}")
    



