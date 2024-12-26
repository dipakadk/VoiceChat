from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.runnables.history import RunnableWithMessageHistory
from models.handler_imports import *
from datetime import datetime, timezone
from utils.agent_variables import gdpr_instruction_gated, gdpr_instruction_transparent, no_gdpr_instruction_gated, no_gdpr_instruction_transparent, tour_booking_instructions, booking_instructions_rules_important, reschedule_cancel_booking_instructions, reschedule_instructions_rules_important, important_instructions,location_instructions_rules,lead_instructions_rule
from utils.redis_whatsapp import getData
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from tools.setup_tool import *
from datetime import datetime
import html2text
from langchain.schema.output_parser import StrOutputParser
output_parser = StrOutputParser()
#tools
from tools.setup_tool import GetCustomTools
from tools.intentChain import get_intent
#utils
from utils.get_prompts import get_prompts







def get_tool_func(tools):
    tools_final =[]
    functions = [convert_to_openai_function(t) for t in tools]
    for functi in functions:
        dict_1 = {'type': 'function'}
        dict_1.update(functi)
        tools_final.append(dict_1)
    return tools_final



import re
import os
import json
import time
import base64
import asyncio
import argparse
from twilio.rest import Client
from datetime import datetime,timezone
from fastapi import FastAPI, WebSocket
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv

from langchain.schema.output_parser import StrOutputParser
today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")

load_dotenv(find_dotenv())

from chains.prompt import phoneServiceInstance


async def init_tool(request_data):
    global phoneServiceInstance
    time1=datetime.now()
   
    # prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'agent_template',False,request_data.org_name,request_data.chatbot_name))
    # if request_data.agent=="outboundCall":
    #     prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'outboundCall_template',False,request_data.org_name,request_data.chatbot_name))
    if request_data.query in ["/dummy_welcome"]:
        request_data.history.clear()
    
    time_before = datetime.now()
    toolsInstance=await GetCustomTools.create(request_data)
    time_after = datetime.now()
    print("Total initialization", time_after-time_before)
    tools=await toolsInstance.get_tools()
    tool_names=await toolsInstance.get_tools_names()
    print(tools)
    print()
    print()
    print()
    print("History Sender is ==================",request_data.history_sender_branch)
    print("Booked Flag value is ==============================",request_data.flagBooked)

    print()
    print()
    print()
    if request_data.prompt not in [None, "", " ", "string", "<p><br></p>"]:
        
        markdown_converter = html2text.HTML2Text()
        markdown_text = markdown_converter.handle(request_data.prompt)

        # print("Updated prompt after HTML To Text is===============",markdown_text)

        prompt_agent = ChatPromptTemplate.from_messages(
            [
                ("system", markdown_text),
                ("placeholder", "{chat_history}"),
                ("human", "{query}"),
                ("placeholder", "{agent_scratchpad}")
            ],
        )
    elif request_data.agent=="OutboundPhoneCall":
        prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'outboundCall_template',False,request_data.org_name,request_data.chatbot_name))
        print("Prompt agent outbound call selected")
    elif request_data.agent=="Email":
        prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'email_template',False,request_data.org_name,request_data.chatbot_name))
    elif request_data.agent=="inboundCall":
        prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'inboundCall_template',False,request_data.org_name,request_data.chatbot_name))
    else:
        prompt_agent = ChatPromptTemplate.from_messages(get_prompts(None,'agent_template_gated',False,request_data.org_name,request_data.chatbot_name,request_data))
    
    
    

    
    final_tools_array = get_tool_func(tools)
    
    phone = "+9779869035670"
    
    
    from callservice import AIPhoneService
    phoneServiceInstance = AIPhoneService(system_message=prompt_agent, tools=final_tools_array, phone_number_to_call=phone)

    await phoneServiceInstance.make_call()
    
    




