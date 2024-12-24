import datetime
# from langchain_core.messages import HumanMessage, AIMessage
from services.http_api import http_post
from typing import Optional
import pytz
from fastapi import HTTPException
import validators
import json
from bson import ObjectId
import json

class HumanMessage:
    def __init__(self, content):
        self.content = content

class AIMessage:
    def __init__(self, content):
        self.content = content
        
async def extract_message(messages,welcome_message:str=None):
    
    notes = ""
    if not welcome_message:
        for i in range(0, len(messages), 2):
            human_message = messages[i].content if i < len(messages) else ""
            ai_message = messages[i+1].content if i+1 < len(messages) else ""
            if human_message:
                notes += f"<p>Human: {human_message.replace('<p>','').replace('</p>','')}</p>"
            if ai_message:
                notes += f"<p>AI: {ai_message.replace('<p>','').replace('</p>','')}</p>"
            # notes.append({"human": human_message, "AI": ai_message})
    else:
        for i in range(0, len(messages), 2):
            ai_message = messages[i].content if i < len(messages) else ""
            human_message = messages[i+1].content if i+1 < len(messages) else ""
            # notes.append({"AI": ai_message,"human": human_message})
            if ai_message:
                notes += f"<p>AI: {ai_message.replace('<p>','').replace('</p>','')}</p>"
            if human_message:
                notes += f"<p>Human: {human_message.replace('<p>','').replace('</p>','')}</p>"
    formatted_messages = {"note": notes}
    return formatted_messages

def post_event_to_crm(request_data,history,identifier):
    print(request_data,"----------------------",request_data.agent)
    crm_api_url=request_data.crm_api_url
    crm_data = {
        "type": "history",
        "agent": request_data.agent or 'web',
        "date": datetime.datetime.now().astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "note": history,
        "email": identifier,
        "venue_name": "Keepme Fit Club"
    }
    headers = {'Content-Type': 'application/json'}
    post_event_in_crm = http_post(url=f'{crm_api_url}/h7KpT3fDqRvJbZx', headers=headers, data=crm_data)
    print(post_event_in_crm,"posted in crm")
    
    
# def generate_streaming_response(data,result,call_id):
#     message_id=f'chatcmpl-{call_id}'
#     if message_id:
#         static_message = {
#             "id": f"{message_id}",
#             "choices": [
#                 {
#                     "delta": {
#                         "content": result,
#                         "function_call": None,
#                         "role": None,
#                         "tool_calls": None
#                     },
#                     "finish_reason": None,
#                     "index": 0,
#                     "logprobs": None
#                 }
#             ],
#             "created": 1722962157,
#             "model": "gpt-3.5-turbo-0125",
#             "object": "chat.completion.chunk",
#             "service_tier": None,
#             "system_fingerprint": None,
#             "usage": None
#         }
#         json_data = json.dumps(static_message)

#         yield f"data:{json_data}\n\n"
        

async def validate_url(url: Optional[str]):
    if url and not validators.url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    
    
class DotDict(dict):
    """Dictionary with dot notation access."""
    def __getattr__(self, attr):
        return self.get(attr)
    
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    
    
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    