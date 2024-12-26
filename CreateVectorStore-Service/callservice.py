import re
import os
import json
import time
import base64
import asyncio
import argparse
import websockets
from twilio.rest import Client
from datetime import datetime,timezone
from fastapi import FastAPI, WebSocket
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from fastapi.websockets import WebSocketDisconnect
from langchain.schema.output_parser import StrOutputParser




load_dotenv(find_dotenv())

from chains.prompt import get_routes_router
ROUTER = get_routes_router()

today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")



class AIPhoneService:
    def __init__(self, phone_number_to_call:str, system_message: str, tools: list):
        self.SYSTEM_PROMPT:str= system_message
        self.PHONE_NUMBER_TO_CALL:str = phone_number_to_call
        self.TOOLS: list = tools

        self.TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
        self.TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
        self.PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
        self.OPENAI_API_KEY = os.getenv('OPEN_API_KEY')
        self.raw_domain = os.getenv('DOMAIN', '')
        self.DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', self.raw_domain)
        
        self.VOICE = 'alloy'
        self.LOG_EVENT_TYPES = [
            'error', 'response.content.done', 'rate_limits.updated', 'response.done',
            'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
            'input_audio_buffer.speech_started', 'session.created'
        ]


        if not (self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN and self.PHONE_NUMBER_FROM and self.OPENAI_API_KEY):
            raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')
        self.client = Client(self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN)


        self.name = "Ajeet Acharya"
    




    async def send_initial_conversation_item(self, openai_ws):
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
                            f"Greet the user with hi, hello, or any other greeting without using any tools. With their name: {self.name}"
                        )
                    }
                ]
            }
        }

        await openai_ws.send(json.dumps(initial_conversation_item))
        await openai_ws.send(json.dumps({"type": "response.create"}))

    async def initialize_session(self, openai_ws):
        """Control initial session with OpenAI."""
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": self.VOICE,
                "instructions": self.SYSTEM_PROMPT,
                "modalities": ["text", "audio"],
                "temperature": 0.9,
                "tools": self.TOOLS,
                "tool_choice": "auto",
            }
        }
        print('Sending session update:', json.dumps(session_update))
        await openai_ws.send(json.dumps(session_update))

        # Have the AI speak first
        await self.send_initial_conversation_item(openai_ws)

    async def make_call(self):
        """Make an outbound call."""
        outbound_twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Connect><Stream url="wss://1c88-111-119-49-232.ngrok-free.app/llm/media-stream" /></Connect></Response>'
        )
        
        call = self.client.calls.create(
            from_=self.PHONE_NUMBER_FROM,
            to=self.PHONE_NUMBER_TO_CALL,
            twiml=outbound_twiml
        )
        await self.log_call_sid(call.sid)
        
    async def log_call_sid(self, call_sid):
        """Log the call SID."""
        print(f"Call started with SID: {call_sid}")
        

    @ROUTER.websocket('/media-stream')
    async def handle_media_stream(self,websocket: WebSocket):
        """Handle WebSocket connections between Twilio and OpenAI."""
        OPENAI_API_KEY = self.OPENAI_API_KEY
        

        
        async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            await self.initialize_session(openai_ws)
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
                        if response['type'] in self.LOG_EVENT_TYPES:
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
                            print("----------function is called-------------------")
                            try:
                                function_name = response['name']
                                print("=====================================>",function_name)
                                call_id = response['call_id']
                                arguments = json.loads(response['arguments'])
                                
                                functions_available = {
                                }

                                if function_name in functions_available.keys():
                                    start_time = time.time()
                                    result = functions_available[function_name](arguments)
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
            
        

        