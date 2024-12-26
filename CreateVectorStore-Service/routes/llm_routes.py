from fastapi import  APIRouter,UploadFile, File,HTTPException, Request,BackgroundTasks,Query
router = APIRouter()
from typing import List,Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader,TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import Docx2txtLoader
from fastapi.responses import StreamingResponse
from datetime import datetime,timedelta, timezone
import uuid
import io
import base64, asyncio
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



from fastapi.websockets import WebSocket


from tools import *   


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
import time

client = OpenAI(api_key=OPEN_API_KEY)
embedding_type="openai"
vector_database={}
EmbeddingIns = Embedings(embedding_type=embedding_type)
embedings = EmbeddingIns.get_embedings()
llm = EmbeddingIns.get_llm(0, MODAL)


#Initialised S3 Bucket
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

from fastapi import Query
from typing import List, Optional, Union, Annotated
@router.post("/vectordb/create-store")
async def create_store(
    organization_id: str,
    region_id:Optional[str]=None,
    branch: Optional[str] = None,
    uploaded_by:Optional[str] = None,
    intent: Optional[str] = "Default",
    clearOldDocuments:Optional[bool] = False,
    url: Annotated[list[str] | None, Query()]  = None,
    files: List[UploadFile] = File(...),
):
    try:
        print("intent is==========",intent)
        created_collections = []
        combined_documents = []
        file_metadata_list = []
        return_data = None
        
        if branch:
            collection_name = f'general_info_{organization_id}_{branch}'
            old_collection_name=f'general_info_{branch}_{organization_id}'
        elif region_id and not branch:
            collection_name = f'general_info_{organization_id}_{region_id}'
            old_collection_name=f'general_info_{region_id}_{organization_id}'
        else:
            collection_name = f"general_info_{organization_id}"
            old_collection_name=f'general_info_{organization_id}'
        print("url is==========",url)
        # Process URL if provided
        if url and url != ['']:
            for u in url:
                await validate_url(u)
                documents = web_extractor(u,intent,region_id,branch)
                if documents:
                    combined_documents.extend(documents) 
                print("Length of url documents===============",len(documents))
                print("Extracted content for url: ",u)
        
        # Convert single file to list if necessary
        if files and not isinstance(files, list):
            files = [files]
        
        if files:
            for uploaded_file in files:
                file_extension = uploaded_file.filename.split(".")[-1].lower()
                unique_filename = f"{organization_id}_{uuid.uuid4()}_{uploaded_file.filename}"
                temp_file_path = f"{unique_filename}"

                try:
                    contents = await uploaded_file.read()
                    # Upload file to S3
                    # with io.BytesIO(contents) as file_content:
                    #     s3.upload_fileobj(file_content, BUCKET_NAME, unique_filename)
                    s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

                    # Save file temporarily for processing
                    with open(temp_file_path, "wb") as f:
                        f.write(contents)
                    
                    print("Temp file saved")

                    # Process the file based on its type
                    if file_extension == "pdf":
                        docs=[]
                        loader = PyMuPDFLoader(temp_file_path)
                        documents = loader.load()
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
                        documents = text_splitter.split_documents(documents=documents)
                        for index,item in enumerate(documents):
                            docs.append(Document(page_content=item.page_content,
                                                      metadata={"source":s3_url,
                                                      "type":file_extension,
                                                      "filename":uploaded_file.filename,
                                                      "intent":intent,
                                                      "region_id":region_id or "Default",
                                                      "branch": branch or "Default"
                                                      }))
                        combined_documents.extend(docs)
                        print("total length of document file==========",len(docs))
                        print("One of the metadata====================",docs[0].metadata)
                        
                                            # Process the file based on its type
                    elif file_extension in ["docx","docs"]:
                        docs=[]
                        loader = Docx2txtLoader(temp_file_path)
                        documents = loader.load()
                        for index,item in enumerate(documents):
                            docs.append(Document(page_content=item.page_content,
                                                      metadata={"source":s3_url,
                                                      "type":file_extension,
                                                      "filename":uploaded_file.filename,
                                                      "intent":intent,
                                                      "region_id": region_id or "Default",
                                                      "branch": branch or "Default"
                                                      }))
                        combined_documents.extend(docs)

                    elif file_extension == "csv":
                        loader = CSVLoader(temp_file_path,encoding="utf-8")
                        docs=[]
                        documents = loader.load()
                        for index,item in enumerate(documents):
                            docs.append(Document(page_content=item.page_content,
                                                      metadata={"source":s3_url,
                                                      "type":file_extension,
                                                      "filename":uploaded_file.filename,
                                                      "intent":intent,
                                                      "region_id": region_id or "Default",
                                                      "branch": branch or "Default"
                                                      }))
                        combined_documents.extend(docs)

                    elif file_extension == "txt":
                        docs=[]
                        loader = TextLoader(temp_file_path,encoding="utf-8")
                        documents = loader.load()
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
                        documents = text_splitter.split_documents(documents=documents)
                        for index,item in enumerate(documents):
                            docs.append(Document(page_content=item.page_content,
                                                      metadata={'source':s3_url,
                                                      'type':file_extension,
                                                      "filename":uploaded_file.filename,
                                                      "intent":intent,
                                                      "region_id": region_id or "Default",
                                                      "branch":branch or "Default"
                                                      }))
                        combined_documents.extend(docs)
                    
                    elif file_extension == "xlsx":
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_csv_file:
                            try:
                                df = pd.read_excel(temp_file_path)
                                df.to_csv(temp_csv_file.name, index=False)
                                loader = CSVLoader(file_path=temp_csv_file.name,encoding="utf-8")
                                documents = loader.load()
                                docs = []

                                for index, item in enumerate(documents):
                                    docs.append(
                                        Document(page_content=item.page_content,
                                                 metadata={
                                                     "source": s3_url, "type": file_extension, "filename": uploaded_file.filename, "intent": intent, "region_id": region_id or "Default","branch": branch or "Default"
                                                 })
                                    )
                                combined_documents.extend(docs)
                            except Exception as e:
                                print(f"Error {e}")
                            finally:
                                if os.path.exists(temp_csv_file.name):
                                    os.remove(temp_csv_file.name)
                                                    

                    # Prepare file metadata for MongoDB
                    file_metadata = FileMetadataModel(
                        filename=unique_filename,
                        original_filename=uploaded_file.filename,
                        upload_date=datetime.now(timezone.utc),
                        content_type=uploaded_file.content_type,
                        s3_url=s3_url
                    )
                    file_metadata_list.append(file_metadata.model_dump())
                    print("done here")

                except Exception as loader_error:
                    print(f"Error processing {uploaded_file.filename}: {loader_error}")
                    continue  
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

        if combined_documents:
            store_arguments = {
                'collection_name': collection_name,
                'embedding_type': 'openai',
                "store_type": 'milvus',
                "data": combined_documents,
                "host": MILVUS_HOST,
                "port": MILVUS_PORT,
                "db_name":DB_NAME
            }
            vectorstoreArgs={
                'collection_name': collection_name,
                'old_collection_name':old_collection_name,
                'embedding_type': 'openai',
                "store_type": 'milvus',
                "data": combined_documents,
                "host": MILVUS_HOST,
                "port": MILVUS_PORT,
                "db_name":DB_NAME
            }
            print("Store arguments entered")
            store = VectorStore(**vectorstoreArgs)
            print("before store documents")
            await store.store_documents(file_extension='combined',clearOldDocuments=clearOldDocuments)
            print("after store documents")
            created_collections.append(store_arguments['collection_name'])
            
            res=await vectorstore_info_collection.update_many(
                {"vectorstore_collection": collection_name,"intent":intent, "region_id":region_id, "branch":branch},
                {"$set": {"replaced": True}}
             )
            
            if url == ['']:
                url = None
            # Save file metadata and collection info to MongoDB
            print("Here here here")
            vectorstore_info = VectorStoreInfoModel(
                files=file_metadata_list,
                url=url,
                organization_id=organization_id,
                uploaded_by=uploaded_by,
                branch=branch,
                region_id=region_id,
                vectorstore_collection=collection_name,
                intent=intent,
                created_date=datetime.now(timezone.utc),
                updated_date=datetime.now(timezone.utc)
            )
            insert_result = await vectorstore_info_collection.insert_one(vectorstore_info.model_dump())
            saved_data = await vectorstore_info_collection.find_one({"_id": insert_result.inserted_id})
            return_data = VectorStoreInfoModel(**saved_data)

        return {
            "message": "success",
            "data": return_data
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}





#similarity search tool
@router.get("/vectordb/similarity/search")
async def get_similarity_search(organization_id:str,query:Optional[str]=None,TopK:Optional[int]=3,branch:Optional[str]=None,region_id:Optional[str]=None,expression:Optional[str]="type == 'csv'"):
    if branch:
        collection_name = f'general_info_{organization_id}_{branch}'
    elif region_id and not branch:
        collection_name = f'general_info_{organization_id}_{region_id}'
    else:
        collection_name = f"general_info_{organization_id}"
    collection=await MilvusVectoreStore(host=MILVUS_HOST,port=MILVUS_PORT).has_collection(collection_name)
    collections_list=await MilvusVectoreStore(host=MILVUS_HOST,port=MILVUS_PORT).list_collections()
    print(collection,collections_list)
    if collection:
        EmbeddingIns = Embedings(embedding_type='openai')
        embedings = EmbeddingIns.get_embedings()

        vectorstore=VectorStore.get_store(
                embedings, 'milvus', collection_name, MILVUS_HOST, MILVUS_PORT
            )
        
        
        filter_docs=[]
        total_docs=0
        similarity=[]
        if expression:
            expr = expression or "type == 'text'"
            filter_docs=vectorstore.get_documents(expr)
            total_docs=len(filter_docs)  
              
        if query:
            similarity=vectorstore.similarity_search(query,k=TopK)
        
        return {"query": query,"similarity":similarity,"filterByMetadata":{'total':total_docs,'docs':filter_docs}}
    else:
        return {"error": "collection not found"}


from langchain_core.chat_history import InMemoryChatMessageHistory

#generate response from
from openai import OpenAI
import json
client = OpenAI(api_key=OPEN_API_KEY)





def generate_streaming_response(data,result,call_id):
    print(result,"result datat")
    message_id=f'chatcmpl-{call_id}'
    if message_id:
        static_message = {
            "id": f"{message_id}",
            "choices": [
                {
                    "delta": {
                        "content": result,
                        "function_call": None,
                        "role": None,
                        "tool_calls": None
                    },
                    "finish_reason": None,
                    "index": 0,
                    "logprobs": None
                }
            ],
            "created": 1722962157,
            "model": "gpt-3.5-turbo-0125",
            "object": "chat.completion.chunk",
            "service_tier": None,
            "system_fingerprint": None,
            "usage": None
        }
        json_data = json.dumps(static_message)

        yield f"data:{json_data}\n\n"



LOG_EVENT_TYPES = [
            'error', 'response.content.done', 'rate_limits.updated', 'response.done',
            'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
            'input_audio_buffer.speech_started', 'session.created'
        ]




@router.post("/vapi/chat/completions")
async def generate_compilation(request: Request,background_tasks: BackgroundTasks):
    global vector_database

    request_data = await request.json()
    print(request_data,"requestata")
    stream = request_data.get("stream", False)
    user_query = next(
        (message['content'] for message in reversed(request_data['messages']) if message['role'] == 'user'),
        None
    )
    variable_values = request_data.get('call', {}).get('assistantOverrides', {}).get('variableValues', {})
    

    call_id = request_data['call']['id']
    request_data.pop('call', None)
    request_data.pop('metadata', None)
    request_data.pop('phoneNumber', None)
    request_data.pop('customer', None)

    whatsappInitialMessage = None
   
    branch_id=variable_values.get("details",{}).get("branch_details", {}).get("_id", None)
    org_id=variable_values.get("details",{}).get("client_details",{}).get("_id",None)

 
    branch_collection_name = f"general_info_{org_id}_{branch_id}"
    if branch_collection_name not in vector_database:
        vector_database[branch_collection_name] = VectorStore.get_store(
            embedings, 'milvus', branch_collection_name, MILVUS_HOST, MILVUS_PORT
        )

    database_general =None
    database_branch = vector_database.get(branch_collection_name, None)
    
    actual_sender = call_id
    
    
    client_name=variable_values.get("details",{}).get("client_details",{}).get("name",None)
    client_address=variable_values.get("details",{}).get("client_details",{}).get("address",None)
    client_email=variable_values.get("details",{}).get("client_details",{}).get("email",None)
   
    
    branch_name= variable_values.get("details",{}).get('branch_details', {}).get("name", None)
    branch_address= variable_values.get("details",{}).get('branch_details', {}).get("address", None)
    branch_email=variable_values.get("details",{}).get('branch_details', {}).get("email", None)
    brach_phone= variable_values.get("details",{}).get('branch_details', {}).get("phone", None)
    timezone_ = variable_values.get("details",{}).get("branch_details", {}).get("timezone", None)
    region_id = variable_values.get("details",{}).get("branch_details", {}).get("region_id", None)


    if timezone_ and timezone_.startswith("Etc/GMT"):
        timezone_ = timezone_.replace("+", "TEMP").replace("-", "+").replace("TEMP", "-")

    countryCode = variable_values.get("details",{}).get("branch_details", {}).get("countryCode", None)

   
    sender=call_id

    type_ = "transparent"
    gdpr = "true"
    
  
    metadata={
        "name":variable_values.get("Name",None),
        "first_name":variable_values.get("FirstName",None),
        "last_name":variable_values.get("LastName",None),
        "email":variable_values.get("Email",None),
        "phoneNumber":variable_values.get("Phonenumber",None),
    }
   
    
    metadata["gdprLlm"] = gdpr
    metadata["type"] = type_
   
    data={}
    generate_response_instance=None
    agent="Outbound-call"
   

    try:
        data = {
            "query":user_query,
            "stream": False,
            "sender": sender,
            "org_name":client_name,
            "chatbot_name": client_name,
            "response_content_line": 70,
            "prompt": "",
            "out_of_context_response": None,
            "general_collection_name": None,
            "branch_collection_name":branch_collection_name,
             "general_database":None,
             "branch_database":database_branch,
            "org_id": org_id,
            "branch":branch_id,
            "embedding_type": embedding_type,
            "whatsappInitialMessage": whatsappInitialMessage,
            "modal": MODAL,
            "host": MILVUS_HOST,
            "port": MILVUS_PORT,
            "vapiHistory": None,
            "redis_server": REDIS_SERVER,
            "agent": agent,
            "actual_sender":actual_sender,
            'venue_id':None,
            'whatsapp_number': None,
            'region_id': region_id,
            "WantsLocation": False,
            "requiredLanguage":"English",
            "toolinvoked":False,
            #client details
           "client_details":{
                "client_name":client_name,
                "client_address":client_address,
                "client_email":client_email,
                "branch_name":branch_name,
                "branch_email":branch_email,
                "branch_address":branch_address,
                "branch_phone_number":brach_phone,
                "countryCode": countryCode,
                "timezone": timezone_
           },
            
            #calander services
            "calander_api_url":CALANDER_API_URL,
            "calander_api_key":CALANDER_API_KEY,
            "calander_name":CALANDER_NAME,
            "calanderid_book_tour":CALANDER_ID_BOOK_TOUR,
            "crm_api_url":CRM_API_URL,
            "metadata":metadata,
            "isVistor_new":True,
            "background_tasks":background_tasks,
            "unhandled_arguments":True,
            "user_intent":None,
            "embedings":embedings,
            "llm":llm,
            "useRegion":False,
           
            "type": type_,
            "gdpr": gdpr,
            "welcome_message":None,
            "booking_tour_fields": {
                    'date': "Date that was collected for booking",
                    'time': "Time that was collected for booking",
                    'firstname': "First name of the user",
                    'lastname': "Last name of the user",
                    'email': "Email address of the user",
                    'phonenumber': "Phone number of the user"
                }

        }
        generate_response_instance = GenerateResponse(**data)
        # result, handled, user_intent= await generate_response_instance.generate()

        await generate_response_instance.generate()
        # send_result=result.get("result",'')
        # return StreamingResponse(generate_streaming_response(stream,send_result,call_id), media_type="text/event-stream")


    except HTTPException as e:
        raise e
    except Exception as e:
        print(e,"error")
        if generate_response_instance:
                result= generate_response_instance.generate()
                stream={}
                return StreamingResponse(generate_streaming_response(stream,result,call_id), media_type="text/event-stream")
        else:
                return {"result":"I'm sorry, I don’t have all the details to fully answer your question right now.",'sender':call_id}

from main import *

from pydantic import BaseModel

class CallRequest(BaseModel):
    phone_number: str
    chatbot_name:Optional[str]
    details:dict
    clientId:Optional[str]
    locationId:Optional[str]
    chatbotName:Optional[str]
    orgName:Optional[str]
    

# @router.post('/make-call')
# async def trigger_call(request: CallRequest):
#     """
#     Trigger a call to the provided phone number using Twilio.
#     """
#     phone_number = request.phone_number

#     if not phone_number:
#         raise HTTPException(status_code=400, detail="Phone number is required.")

#     try:
#         await make_call(request.phone_number)
#         # await make_call(phone_number)
#         return {"status": "success", "message": f"Call initiated to {phone_number}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error initiating call: {str(e)}")
 


import websockets
from fastapi.websockets import WebSocketDisconnect

@router.post("/generate/response/chat/completions")
async def get_response(request: QueryRequest,background_tasks: BackgroundTasks):
    global vector_database
    global phoneServiceInstance

    
    isVisitor_new=True
    # email= None
    # phoneNumber= None
    actual_sender = f"{request.sender}"
    

    InitialresponseFacebook = None
    if request.agent.lower() in ["facebook", "instagram"]:
        InitialresponseFacebook = await get_initial_case_facebookInstagram(request) 

    if InitialresponseFacebook:
        return InitialresponseFacebook

    whatsappInitialMessage = None

    tourBooked = False
    sessionExists = False
    

    if request.agent in ["whatsapp", "sms"]:
        request = request.model_copy(update={"sender":request.sender.replace("+","")})
        
        session_exist=await get_active_session(
            email_phone=request.sender, 
            agent=request.agent,
            whatsapp_number=request.whatsapp_number, 
            organization_email=request.organization_email or None
        ) or None
        print("-=================session exists=====",session_exist)
        if session_exist:

            sessionExists = True
            
            search_response = {}
            
            active_session_id = session_exist.get("active_session_id")
            session_branch = session_exist.get("branch") or None
            session_organization_id = session_exist.get("organization_id") or None

            request = request.model_copy(update={"sender":active_session_id})

            search_response["organization_id"] = session_organization_id
            search_response["branch"] = session_branch
            
            to_update = await process_search_response(
                search_response=search_response, 
                sender=request.sender, 
                metadata=request.metadata
            )

            request = request.model_copy(update=to_update)

            initialMessageresult = await findInitialMessage(
                sender=request.sender, 
                whatsapp_number=request.whatsapp_number
            )

            if initialMessageresult:
                if initialMessageresult["initialFlag"]:
                    whatsappInitialMessage = initialMessageresult["ai_message"]

        else:
            search_response = await searchVisitorBySender(
                sender=request.sender, 
                llm=llm, 
                organization_id=request.org_id, 
                region_id=request.org_id, 
                whatsapp_number=request.whatsapp_number, 
                agent=request.agent,
                query=request.query
            )

            if isinstance(search_response, dict):
                to_update = await process_search_response(
                    search_response=search_response, 
                    sender=request.sender, 
                    metadata=request.metadata
                )
                request = request.model_copy(update=to_update)
            else:
                return await process_search_response(
                    search_response=search_response, 
                    sender=request.sender, 
                    metadata=request.metadata
                )

    print("Request body============",request)
    if request.branch and not request.region_id:
        request = request.model_copy(update={
                    "region_id":request.details.get('branch',{}).get("region",None)
                })

    print("Region ID is============",request.region_id)

    if request.region_id:
        request = request.model_copy(
            update={
                "region_id": request.region_id.replace(" ","")
            }
        )

    branch_collection_name = ""
    if request.branch:
        branch_collection_name = f"general_info_{request.org_id}_{request.branch}"

    general_collection_name = (
        f'general_info_{request.org_id}_{request.region_id}' if request.region_id else f'general_info_{request.org_id}'
        )

    if general_collection_name not in vector_database:
        vector_database[general_collection_name] = VectorStore.get_store(
            embedings, 'milvus', general_collection_name, MILVUS_HOST, MILVUS_PORT
        )

    print("General collection=======",general_collection_name)
    print("Branch collection===========",branch_collection_name)

    if branch_collection_name and branch_collection_name not in vector_database:
        vector_database[branch_collection_name] = VectorStore.get_store(
            embedings, 'milvus', branch_collection_name, MILVUS_HOST, MILVUS_PORT
        )

    database_general = vector_database[general_collection_name]
    database_branch = vector_database.get(branch_collection_name, None)
    
    
    
    
  
    # print("is session exist", session_exist)
    
    client_name=request.details.get('client',{}).get("name",None)
    client_address=request.details.get('client',{}).get("address",None)
    client_email=request.details.get('client',{}).get("email",None)
    
    branch_name= request.details.get('branch', {}).get("name", None)
    branch_address= request.details.get('branch', {}).get("address", None)
    branch_email= request.details.get('branch', {}).get("email", None)
    brach_phone= request.details.get('branch', {}).get("phone", None)
    timezone_ = request.details.get("branch", {}).get("timezone", None)

    if timezone_ and timezone_.startswith("Etc/GMT"):
        timezone_ = timezone_.replace("+", "TEMP").replace("-", "+").replace("TEMP", "-")

    countryCode = request.details.get("branch", {}).get("countryCode", None)

    
    sender=f"{request.sender}"

    
    type_ = request.metadata.get("type", "transparent")
    
    gdpr=None
    if request.agent.lower() not in ["web"]:
        gdpr = None 
    else:
        gdpr = request.metadata.get("gdprLlm",None)
    
    #get visitor details if available
    visitor_details=await get_visitor_details(sender,request.org_id,request.branch,request.region_id)
    metadata=request.metadata
    if visitor_details and visitor_details.get('details', None):
         metadata=visitor_details.get('details')
    
    # metadata["gdprLlm"] = gdpr
    # metadata["type"] = type_
    print(metadata,sender,"==============visitor details=====================")
    data={}
    generate_response_instance=None
    agent=request.agent.lower()
    




    try:
        data = {
            "query": request.query,
            "stream": request.stream,
            "sender": sender,
            "org_name": request.organization_name or "keepmefit Club",
            "chatbot_name": request.chatbot_name or "keepmefit Club",
            "response_content_line": 70,
            "prompt": request.prompt or "",
            "out_of_context_response": None,
            "general_collection_name": general_collection_name,
            "branch_collection_name":branch_collection_name,
             "general_database":database_general,
             "branch_database":database_branch,
            "org_id": request.org_id,
            "branch":request.branch,
            "embedding_type": embedding_type,
            "whatsappInitialMessage": whatsappInitialMessage,
            "modal": MODAL,
            "host": MILVUS_HOST,
            "port": MILVUS_PORT,
            "vapiHistory": None,
            "redis_server": REDIS_SERVER,
            "agent": agent,
            "actual_sender":actual_sender,
            'venue_id':request.venue_id,
            'whatsapp_number': request.whatsapp_number,
            'region_id': request.region_id,
            "WantsLocation": False,
            "requiredLanguage":"English",
            "toolinvoked":False,
            #client details
           "client_details":{
                "client_name":client_name,
                "client_address":client_address,
                "client_email":client_email,
                "branch_name":branch_name,
                "branch_email":branch_email,
                "branch_address":branch_address,
                "branch_phone_number":brach_phone,
                "countryCode": countryCode,
                "timezone": timezone_
           },
            
            #calander services
            "calander_api_url":CALANDER_API_URL,
            "calander_api_key":CALANDER_API_KEY,
            "calander_name":CALANDER_NAME,
            "calanderid_book_tour":CALANDER_ID_BOOK_TOUR,
            "crm_api_url":CRM_API_URL,
            "metadata":metadata,
            "isVistor_new":isVisitor_new,
            "background_tasks":background_tasks,
            "unhandled_arguments":True,
            "user_intent":None,
            "embedings":embedings,
            "llm":llm,
            "tourBooked": tourBooked,
            "sessionExists": sessionExists,
            "organization_email": request.organization_email,
            "useRegion":request.useRegion,
           
            "type": type_,
            "gdpr": gdpr,
            "welcome_message":request.welcome_message or None,
            "booking_tour_fields": {
                    'date': "Date that was collected for booking",
                    'time': "Time that was collected for booking",
                    'firstname': "First name of the user",
                    'lastname': "Last name of the user",
                    'email': "Email address of the user",
                    'phonenumber': "Phone number of the user"
                }

        }
        

        generate_response_instance = GenerateResponse(**data)
        if request.stream in [True, "True", "true"]:
            return StreamingResponse(generate_response_instance.generate_streaming_response(), media_type="text/event-stream")

        result, handled, user_intent,sessionExists, tourBooked= await generate_response_instance.generate()
        # print("result===============",result)
        
        # #create visitors and message history
        visitor_data = Visitor(
            sender=sender,
            agent=[agent],
            branch=request.branch,
            organization_id=request.org_id,
            region_id=request.region_id,
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc),
        )
        if agent in ['fb','facebook','whatsapp','instagram','sms']:
            visitor_data = Visitor(
            sender=sender,
            agent=[agent],
            details=metadata,
            organization_id=request.org_id,
            branch=request.branch,
            region_id=request.region_id,
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc)
            )
        background_tasks.add_task(upsert_visitor, visitor_data)
        
        background_tasks.add_task(create_message, sender=sender, human_message=request.query, ai_message=result.get('result') or result, organization_id=request.org_id, agent=agent, branch=request.branch,handled=handled,intent=user_intent,whatsapp_number=request.whatsapp_number,region_id=request.region_id)
        

        if sessionExists is False and tourBooked is False:
            if request.agent in ["whatsapp", "sms"]:
                session_data = {
                    "phone_number": request.sender,
                    "sender": request.sender,
                    "region_id": request.region_id,
                    "branch": request.branch,
                    "organization_id": request.org_id,
                    "whatsapp_number": request.whatsapp_number
            }
                background_tasks.add_task(create_visitors_session,data=session_data)
        
            if request.agent in ["email"]:
                session_data = {
                    "email_address": request.sender,
                    "sender": request.sender,
                    "region_id": request.region_id,
                    "branch": request.branch,
                    "organization_id": request.org_id,
                    "organization_email": request.organization_email
                }

                background_tasks.add_task(create_visitors_session,data=session_data)


        return result

    except HTTPException as e:
        raise e
    except Exception as e:
        print("hi",str(e))
        sorrymessage="I'm sorry, I don’t have all the details to fully answer your question right now."
        return {"result":sorrymessage,'sender':sender}

from callservice import *
from chains.prompt import SYSTEM_PROMPT, tools_functions

                
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
                        call_sid = data['start']['callSid']
                        print(call_sid)
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
                                    # "generalInfo": general_info,
                                    # "check_details": check_details,
                                    # "bookTool": booking_user_form_tool,
                                    # "checkTime": checkTime
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
    



# API endpoint to detaermine top asked questions and intents
@router.get("/history/get/top_questions_and_intents")
async def get_history(
    handled: Optional[bool] = Query(None, description="Filter by handled status"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    region_id: Optional[str] = Query(None, description="Filter by Region ID"),
    intents: List[str] = Query([],description="Queries related to which Intent"),
    limit: int = Query(20, description="Number of results to return"),
    offset: int = Query(0, description="Number of results to skip")
):
    try:
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        # print(intents,"intents")
        history_data = await get_queries(handled=handled, start_date=start_date, end_date=end_date, organization_id=organization_id,branch=branch, limit=limit, offset=offset, region_id=region_id)
        # print(history_data)
        queries = [entry.get("human_message", "") for entry in history_data]
        # print(queries,"sjdasjdbj")
        classification_data=None
        if queries and len(queries) > 0:
            try:
                classification_data=cout_and_classify(queries,llm,intents)
                classification_data["top_intents"] = classification_data.pop("aim")
                #mapping
                
            except Exception as e:
                print(e)
                classification_data=None
        queries=json.loads(json.dumps(classification_data, cls=JSONEncoder)) or []
        return {"success":True,"data":queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train/unanswered")
async def train_unanswered(
    request: TrainingDataRequest
):
    try:
        print("Answer========",request.answer)
        print("Query========",request.query)
        print("Intent================",request.intent)
        if request.branch:
            collection_name = f'general_info_{request.organization_id}_{request.branch}'
        elif request.region_id and not request.branch:
            collection_name = f'general_info_{request.organization_id}_{request.region_id}'
        else:
            collection_name = f"general_info_{request.organization_id}"
        
        print("Collection name is =======",collection_name)
        collection=await MilvusVectoreStore(host=MILVUS_HOST,port=MILVUS_PORT).has_collection(collection_name)

        if collection:
            data = [Document(
                page_content=f"{request.query}: {request.answer}",
                metadata={
                    "source": "None",
                    "type": "txt",
                    "filename": "None",
                    "intent": request.intent or "None",
                    "region_id": request.region_id or None,
                    "branch": request.branch or None
                }
            )]
            store_arguments = {
                    'collection_name': collection_name,
                    'embedding_type': 'openai',
                    "store_type": 'milvus',
                    "data": data,
                    "host": MILVUS_HOST,
                    "port": MILVUS_PORT,
                    "db_name":DB_NAME
                }
            store = VectorStore(**store_arguments)
            await store.store_documents(file_extension='combined',clearOldDocuments=False)
            print("Data appended")
            result = await messages_collection.find_one({"_id": ObjectId(request.message_id)})
            if result:
                update_result = await messages_collection.update_one(
                                {"_id": ObjectId(request.message_id)},
                                    {"$set": {"handled": True}}
                )
                return {
                    "success": True,
                    "message": f"Training completed for query: {request.query}, and 'handled' was set to True."
                }
            else:
                return {
                    "success": False,
                    "message": "No document found with the given message_id."
                }
        else:
            print("No collection found")
            return {"success": False, "message": f"Could not Train, No vector store found "}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def convert_object_id(data):
    if isinstance(data, list):
        return [convert_object_id(item) for item in data]
    elif isinstance(data, dict):
        return {k: str(v) if isinstance(v, ObjectId) else convert_object_id(v) for k, v in data.items()}
    return data

@router.get("/search/files")
async def get_files(
    filename:Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    region_id: Optional[str] =Query(None)
    ):
    try:
        regex_query = {"files.original_filename": {"$regex": filename, "$options": "i"}}
        regex_query["organization_id"] = organization_id
        if branch:
            regex_query["branch"] = branch
        if region_id:
            regex_query["region_id"] = region_id
        projection = {
            "vectorstore_collection": 0
        }
        results = await vectorstore_info_collection.find(regex_query, projection).to_list(length=None)
        results = convert_object_id(results)
        return {"success":True, "data":results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))