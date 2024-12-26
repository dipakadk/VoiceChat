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


def get_tool_func(tools):
    tools_final =[]
    functions = [convert_to_openai_function(t) for t in tools]
    for functi in functions:
        dict_1 = {'type': 'function'}
        dict_1.update(functi)
        tools_final.append(dict_1)
    return tools_final

import os
import json
import base64
import asyncio
import argparse
import time
from main import make_call

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
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

import pytz







async def init_tool(request_data):
    
    await make_call(number="+9779869035670")




