from chains.tool_init import init_tool
from langchain_community.chat_message_histories import RedisChatMessageHistory
from tools.setup_tool import GetCustomTools
from models.handler_imports import  tool_queue
import json, time, asyncio
from services.visitor_create_db import upsert_visitor,create_message
from db.visitors import Visitor
from utils.redis_whatsapp import getData
from datetime import datetime, timezone

import redis


def get_chathistory(history_sender, redis_server):
    history =RedisChatMessageHistory(history_sender, url=f"redis://{redis_server}",ttl=60*60*8)
    messages = history.messages 
    if len(messages) >= 30:
      redis_client = redis.StrictRedis.from_url(f"redis://{redis_server}")
      length=len(messages)
      redis_client.ltrim(history.key, -length ,-length+1) #only keeping the last two message
      messages = history.messages
    return history

class GenerateResponse:
    
    def __init__(self, **requestData):
        for key, value in requestData.items():
            setattr(self, key, value)
        
        if self.agent in ["whatsapp", "sms"]:
            self.history_sender = self.sender + "_" + self.org_id + "_" + self.branch if self.branch else ""
            self.history_sender_branch = self.history_sender
        else:
            self.history_sender=self.sender+"_"+self.org_id+"_"+self.region_id if self.region_id else self.sender+"_"+self.org_id
            self.history_sender_branch = self.history_sender + "_" + self.branch if self.branch else "" 
        
        self.flagBooked = getData(f"{self.history_sender_branch}_booked") or None



        if not self.vapiHistory:
            self.history=get_chathistory(self.history_sender, self.redis_server)
            if self.agent in ["whatsapp", "sms"] and self.whatsappInitialMessage:
                self.history.add_ai_message(self.whatsappInitialMessage)
            elif len(self.history.messages) < 1 and self.welcome_message:
                self.history.add_ai_message(self.welcome_message)
        else:
            self.history = self.vapiHistory

    async def generate(self):
        return await init_tool(self)

    def generate_stream(self):
        init_tool(self)

    async def generate_streaming_response(self):  
        toolsInstance=GetCustomTools(self)
        tools=toolsInstance.get_openai_functions()
        # generate_response_instance = GenerateResponse(**data)
        self.generate_stream()
        appended_value = ""      
        while True:  
            value = tool_queue.get()  
            # if value != "":
                # print("the value is:",value)
            if value == None or tool_queue.empty():
                # print("The value is none")
                tool_queue.task_done()
                chunkData = json.dumps(
                { 
                "id": f"chatcmpl-{int(time.time() * 1000)}",
                "created": int(time.time()),
                "model":'gpt-4o',
                "object":'chat.completion.chunk',
                "service_tier":None,
                "system_fingerprint":None,
                "usage":None,
                "tools":[tools],
                "choices":[
                    {
                        "delta":{
                            "content":None,},
                        "finish_reason":None,
                        "index":0, 
                        "logprobs":None
                        }
                    ],
                }
            )
                
                # print(f"data:{chunkData}\n\n") 
                yield f"data:{chunkData}\n\n" 
                visitor_data = Visitor(
                         sender=self.sender,
                        agent=[self.agent],
                        branch=self.branch,
                        organization_id=self.org_id,
                        region_id=self.region_id,
                        created_date=datetime.now(timezone.utc),
                        updated_date=datetime.now(timezone.utc),
                )
                if self.agent in ['fb','facebook','whatsapp','instagram']:
                    visitor_data = Visitor(
                    sender=self.sender,
                    agent=[self.agent],
                    details=self.metadata,
                    organization_id=self.org_id,
                    branch=self.branch,
                    region_id=self.region_id,
                    created_date=datetime.now(timezone.utc),
                    updated_date=datetime.now(timezone.utc)
                )
                self.background_tasks.add_task(upsert_visitor, visitor_data)
                self.background_tasks.add_task(create_message, sender=self.sender, human_message=self.query, ai_message=appended_value, organization_id=self.org_id, agent=self.agent, branch=self.branch,handled=self.unhandled_arguments,intent=self.user_intent,whatsapp_number=self.whatsapp_number,region_id=self.region_id)

                break
            else:
                appended_value += value
                chunkData = json.dumps(
                { 
                "id": f"chatcmpl-{int(time.time() * 1000)}",
                "created": int(time.time()),
                "model":'gpt-4o',
                "object":'chat.completion.chunk',
                "service_tier":None,
                "system_fingerprint":None,
                "usage":None,
                "tools":[tools],
                "choices":[
                    {
                        "delta":{
                            "content":value,},
                        "finish_reason":None,
                        "index":0, 
                        "logprobs":None
                        }
                    ],
                }
                )
                # print(f"data:{chunkData}\n\n") 
                yield f"data:{chunkData}\n\n" 
                
                tool_queue.task_done()  
                await asyncio.sleep(0.01)
        