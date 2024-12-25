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
from tools.setup_tool import *
from datetime import datetime



today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")
today = date
import re
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
load_dotenv()

from langchain.schema.runnable import RunnableMap
from langchain_core.output_parsers import StrOutputParser
string_parser= StrOutputParser()

import os
api_key = os.getenv('OPENAI_API_KEY')
from langchain_openai import ChatOpenAI

# from tools import convert_date_format, general_tool

from langchain_core.prompts import ChatPromptTemplate
llm = ChatOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
from langchain_community.embeddings import OpenAIEmbeddings
embeddings=OpenAIEmbeddings(api_key=api_key)


# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) 

# SYSTEM_MESSAGE = (
#     """
# You are a customer service AI Assistant for the Fitness Club. Your primary responsibility is to provide concise, accurate, and helpful information using available tools.

# For the queries related to the ice rink,trials, club details like phone number, address you must always invoke "generalInfo" tool.


# ### Conversation Rule ###

#   1. Always represent  using first-person language (e.g., 'we,' 'our team,' or 'at our club'). Instead, use first-person references like 'we' or 'our club' to maintain a natural and personal tone.

#   2. Maintain a warm, friendly, and engaging tone. Keep responses informal where appropriate to build comfort and connection. Always reply in the same language as the user's query for a seamless experience.

#   3. For making the conversations more engaging add follow-up questions like: "Is there anything else I can help you with" based on the conversation with users. Remember these follow-up questions should be in new line.

# ### End of Conversation Rule ###



# ### Tool Usage Rule ###

# Use the tool descriptions to answer the user queries.
# 1. For queries related to Membership plans, membership agreements,pricing, options and prices and any other price related queries always use the 'generalInfo' tool.

# ### End of Tool Usage Rule ###



# ### available time slot ###

# Available time slots for booking tour or trial.

# Monday – Friday  : 07.00 – 21:00

# Saturday – Sunday  : 08.00 – 16.00

# ###available time slot ###

# ###Leads Rules###

# 1. For queries related to classes, membership options, membership cost, equipments, services & facilities, about clubs, free trials, visit pass or tour, opening hours, joining or personal training etc Always follow up with a call to action (CTA) around arranging a tour of the club or offering free trials , using engaging variations that goes seamlessly with the conversations like:

#   -'You can discuss the right membership options for you plus see the gym for yourself when you book a tour of the gym. Would you like me to set that up for you?'

#   -'Would you like me to schedule a tour to experience our facilities?'

#   -'If you have a moment, I'd be happy to set up a free trial to give you a closer look!'

# Remember all your CTA should be in new line.

# ### End of Leads Rules ###


# ###Important###

# Follow the instructions step by step before giving your response.

# 1. Always follow ###Tool Usage Rule### Rule to answers user queries.

# 2. You should always follow the ###Conversation Rule### for making the conversation friendly and engaging.

# ###Important###

# Ensure your response is short, concise, accurate by validating the response from the tool.

# Always follow the instructions within the ###Important### tag. Failure to do so will result in penalties.

# **Ensure to Always provide responses in a natural, conversational style without using bullet points.**

#  """
# )

from chains.prompt import system_prompt

VOICE = 'alloy'






LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]


app = FastAPI()

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

import base64

                
@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)
        stream_sid = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    print("RESPONSE MESSAGE=======================",response)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)
                    if response['type'] == 'session.updated':
                        print("Session updated successfully:", response)
                    if response['type'] == 'response.audio.delta' and response.get('delta'):
                        try:
                            audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_payload
                                }
                            }
                            await websocket.send_json(audio_delta)
                        except Exception as e:
                            print(f"Error processing audio data: {e}")
                    if response['type'] == 'response.function_call_arguments.done':
                        print()
                        print("***********************************function is called*******************")
                        print()
                        functions = {
                            'date_booking': checkTime,
                            'bookTool':booking_user_form_tool ,
                            'generalInfo':general_info,
                            'CancelBookTool':CancelBooking,
                            'RescheduleTourBook':RescheduleBooking,

                        }
                        try:
                            function_name = response['name']
                            print("=====================================>",function_name)
                            call_id = response['call_id']
                            arguments = json.loads(response['arguments'])
                            if function_name in functions.keys():
                                start_time = time.time()
                                result = functions[function_name](arguments)
                                print("Result from function call:", result)
                                end_time = time.time()
                                elapsed_time = end_time - start_time
                                print(f"general_keepme execution time: {elapsed_time:.4f} seconds")
                                function_response = {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": result
                                    }
                                }
                                await openai_ws.send(json.dumps(function_response))
                                await openai_ws.send(json.dumps({"type": "response.create"}))
                        
                        except json.JSONDecodeError as e:
                            print(f"Error in json decode in function_call: {e}::{response}")
                        except Exception as e:
                            print(f"Error in function_call.done: {e}")
                            raise Exception("Close Stream")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
        
        
async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Without invoking any tools Greet the user with `Hello I am AI assisant for the Auchenharvie Leisure Centre.How can i help you today`."
        
                    )
                }
            ]
        }
    }


    # completion = client.chat.completions.create(
    #     model="gpt-4o-audio-preview",
    #     modalities=["text", "audio"],
    #     audio={"voice": "alloy", "format": "wav"},
    #     messages=[{"role": "system", "content": "Greet the user with 'Hello I am AI assisant for the Auchenharvie Leisure Centre.How can i help you today."}],
    # )
    # output_path = "outputs/"
    # wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
    # with open(os.path.join(output_path, "dog.wav"), "wb") as f:
    #     f.write(wav_bytes)

    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))


async def initialize_session(openai_ws):
    global system_prompt
    SYSTEM_MESSAGE = system_prompt  

    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.9,
            "tools": [
                    {
                        "type": "function",
                        "name": "date_booking",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        },
                        "description": "A tour booking that checks availability of requested date."
                    },
                    {
                        "type": "function",
                        "name": "bookTool",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        },
                        "description": "A tool used to book a tour/trial/pass/visit once the user details are confirmed"
                    },
                    {
                        "type": "function",
                        "name": "generalInfo",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        },
            "description":"Use this tool for any queries related to the fitness club related queries, classes, memberships, age requirements,   payments, gym, personal training sessions, sports and massage therapy, member benefits, freezing memberships, changing membership types, cancellation policies, team members, club managers, Personal training, etc",
                    },
            #          {
            #             "type": "function",
            #             "name": "EmailTool",
            #             "parameters": {
            #                 "type": "object",
            #                 "properties": {
            #                     "query": {"type": "string"}
            #                 },
            #                 "required": ["query"]
            #             },
            # "description":"To send necessary email through email if the user requests it expect for Tour booking.",
            #         },
                    {
                        "type": "function",
                        "name": "CancelBookTool",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        },
            "description":"A tool used to cancel booked tour/trial/pass/visit.",
                    },


                    {
                        "type": "function",
                        "name": "RescheduleTourBook",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        },
            "description":"A tool used to reschedule booked tour/trial/pass/visit.",
                    },

                ]
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws)
    



async def make_call():
    """Make an outbound call."""
    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://4cb4-111-119-49-191.ngrok-free.app/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to="+9779844484829",
        twiml=outbound_twiml
    )
    await log_call_sid(call.sid)

async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")
    

import subprocess

if __name__ == "__main__":
    print("main.py called from main")
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', required=False)
    args = parser.parse_args()
    phone_number = args.call
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # call_number = "+9779844484829"
    loop.run_until_complete(make_call())
    uvicorn.run(app, host="0.0.0.0", port=8000)