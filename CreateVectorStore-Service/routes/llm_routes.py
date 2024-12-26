from fastapi import APIRouter,UploadFile, File,HTTPException, Request,BackgroundTasks,Query
from typing import List,Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader,TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import Docx2txtLoader
from fastapi.responses import StreamingResponse
from datetime import datetime,timedelta, timezone
import uuid
import io
import boto3
from openai import OpenAI
import os
from dotenv import load_dotenv
from langchain.schema import Document
from bson import ObjectId
from store.vectorestore_connection import VectorStore
from store.get_embedings_llm import Embedings
from models.schema import QueryRequest, TrainingDataRequest
from controllers.generate_response import GenerateResponse
from store.database.milvus import MilvusVectoreStore
from utils.utils import  validate_url,JSONEncoder
from services.visitor_create_db import get_active_session,upsert_visitor,create_message,get_visitor_details,get_queries,create_visitors_session
from db.db_config import vectorstore_info_collection, messages_collection
from db.vector_store import VectorStoreInfoModel,FileMetadataModel
from db.visitors import Visitor
from services.web_extract_content import web_extractor
from tools.get_top_queries_intents import cout_and_classify
import json
import pandas as pd
import tempfile
from services.http_api import process_search_response
from services.whatsappService import searchVisitorBySender, findInitialMessage
from services.FacebookInstagramService import get_initial_case_facebookInstagram

load_dotenv()
router = APIRouter()



MILVUS_HOST= os.getenv('MILVUS_HOST') 
MILVUS_PORT= os.getenv('MILVUS_PORT')
SECRET_KEY= os.getenv('SECRET_KEY')
CLIENT_API_URL=os.getenv('CLIENT_API_URL')
RESPONSE_CONTENT_LINE=os.getenv('RESPONSE_CONTENT_LINE') or 50
OUT_OF_CONTEXT_RESPONSE=os.getenv('OUT_OF_CONTEXT_RESPONSE') or ""
MODAL=os.getenv('MODAL') or "gpt-3.5-turbo"
REDIS_SERVER=os.getenv('REDIS_SERVER')  or 'localhost'
CALANDER_API_URL=os.getenv('CALANDER_API_URL')
CALANDER_ID_BOOK_TOUR=os.getenv('CALANDER_ID_BOOK_TOUR')
CALANDER_NAME=os.getenv('CALANDER_NAME')
CALANDER_API_KEY=os.getenv('CALANDER_API_KEY')
CRM_API_URL=os.getenv('CRM_API_URL')
OPEN_API_KEY=os.getenv('OPEN_API_KEY')
BUCKET_NAME=os.getenv('BUCKET_NAME')
AWS_ACCESS_KEY_ID=os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY=os.getenv('AWS_SECRET_ACCESS_KEY')
DB_NAME=os.getenv('DB_NAME') or 'General'


client = OpenAI(api_key=OPEN_API_KEY)
embedding_type="openai"
vector_database={}
EmbeddingIns = Embedings(embedding_type=embedding_type)
embedings = EmbeddingIns.get_embedings()
llm = EmbeddingIns.get_llm(0, MODAL)

import websockets
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect

from main import *
from chains.prompt import *

                
@router.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    
    await websocket.accept()

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
        extra_headers={
            "Authorization": f"Bearer {OPEN_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
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
                        call_sid = data['start']['callSid']
                        prompt_dict = getData(call_sid)
                        prompt = prompt_dict['prompt'] 
                        await initialize_session(openai_ws, prompt)
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
                                "book_tool":book_tool,
                                "general_keepme":general_keepme,
                                "reschedule_tool":reschedule_tool,
                                "cancel_tool":cancel_tool
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
    
    
class CallRequest(BaseModel):
    phone_number: str
    details:dict
    clientId:str
    locationId:str
    chatbotName:str
    orgName:str



@router.post('/make-call')
async def trigger_call(request: CallRequest):
    system_prompt = f"""Y  You are a digital Sales Assistant named: {request.chatbotName} for {request.orgName}, {request.locationId}. 
    You are having phone conversation with the prospect lead who encourages to the lead to book a tour and provide concise & accurate response using the available tools.    
This is the most important instruction that you need to follow for the user query in order to achieve better accuracy. Invoke the 'GeneralInfo' tool for this query.Do not respond to such queries directly, as doing so violates the rules.
When invoking the 'generalInfo' tool, ensure the `query` argument is concise and relevant to the user's input. Do not include names like `{request.chatbotName}, {request.orgName}, in the query unless explicitly mentioned in the user's query. Focus on the user's specific request without unnecessary additions.
Do not answer on your own Even if you already know the answer to it. You need to invoke the 'generalInfo' tool for it strictly to avoid violation.
If you do not invoke the 'generalInfo' tool to answer for this query, it will violate the rule, so you must invoke the 'generalInfo' tool even if you already have the answer to it from previous conversations.

    You are provided with the users details in metadata inside a double backtick:``{request.details}``
     <Tool Usage Rule>
        1. Use the tools provided in single backticks: (`book_tool`, `reschedule_tool`, `cancel_tool`).
    <Important> 
        Follow the instructions step by step before giving your response.
            1. Always follow <Tool Usage Rule> Rule to answers user queries.
    </Important>
    Ensure your response is short, concise, accurate by validating the response from the tool, and include only the requested information.                    
    Always follow the instructions within the <Important> tag. Failure to do so will result in penalties.
                    
    
    Todays date is {date}, {day_of_week}.
    The available time for booking a tour are:
            -Mondays-Thursdays from 5:30 AM to 9 PM
            -Fridays from 5:30 AM to 7 PM
            -Saturdays-Sundays from 8 AM to 1 PM.
    1. Before invoking `book_tool` and `reschedule_tool` ensure that you ask the user their preferred date and time for the booking .
    DO NOT PASS EMPTY STRINGS IF THE VALUE NOT PROVIDED BY THE USER. KEEP ASKING THE USER TO PROVIDE THE DETAILLS IF THEY ARE MISSING.
    You must always use the tool for answering the questions related to the {request.chatbotName}, {request.orgName}
    Do not response with you own. Always use the tool.
    """
    
    prompt = system_prompt

    
    await make_call(number=request.phone_number, prompt = prompt)