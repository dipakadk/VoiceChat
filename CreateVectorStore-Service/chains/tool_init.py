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
    

    print("History Sender is ==================",request_data.history_sender_branch)
    print("Booked Flag value is ==============================",request_data.flagBooked)

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
    
    if request_data.stream in [True, "true", "True"]:
        model = os.getenv("MODAL")
        streaming_llm = get_streaming_llm(model=model)
        agent = create_tool_calling_agent(streaming_llm,tools, prompt_agent)
        agent_executor = AgentExecutor(tools = tools,
                                        return_intermediate_steps= True, 
                                        handle_parsing_errors=True,
                                        max_iterations= 10, 
                                        early_stopping_method ='generate',
                                        agent= agent,
                                        callbacks = [tool_handler],
                                        verbose=True
                                        )
    else:
        # print(request_data.llm)
        print("Before tool calling agent")
        agent = create_tool_calling_agent(request_data.llm,tools, prompt_agent)
        agent_executor = AgentExecutor(tools = tools,
                                    return_intermediate_steps= True, 
                                    handle_parsing_errors=True,
                                    max_iterations= 10, 
                                    early_stopping_method ='generate',
                                    agent= agent,
                                    verbose=True
                                    )
        print("After executor")
    
    # print("\n\n========",request_data.summerize_history.load_memory_variables({}),"=============memory buffer")

    with get_openai_callback() as cb:
            agent_with_chat_history = RunnableWithMessageHistory(
                    agent_executor,
                    lambda session_id: request_data.history,
                    input_messages_key="query",
                    history_messages_key="chat_history",
                    verbose=True
                )
            config = {"configurable": {"session_id": request_data.history_sender}}
            # print("History===========================",request_data.summerize_history)
            intent_response = await get_intent(query=request_data.query, llm=request_data.llm, history=request_data.history)
            request_data.requiredLanguage = intent_response.get("language")
            important = intent_response.get("intent")
            print("Intent is==========",important)
            booking = ""
            booking_2 = ""
            lead_rules = ""

            important_prompt = important_instructions if important in ["yes", "Yes"] else ""

            gdpr_status = request_data.gdpr  
            request_type = request_data.type

            if request_data.agent not in ["OutboundPhoneCall"]:
                if request_type == "gated":
                    instruction =  no_gdpr_instruction_gated if gdpr_status in ["false"] else gdpr_instruction_gated
                else:
                    instruction =  no_gdpr_instruction_transparent if gdpr_status in ["false"] else gdpr_instruction_transparent
            else:
                instruction = ""
                
            if important not in ["yes", "Yes"]:
                if request_data.branch:
                    if not request_data.flagBooked:
                        if gdpr_status not in ["false"]:
                            booking = tour_booking_instructions
                            booking_2 = booking_instructions_rules_important
                            lead_rules = lead_instructions_rule
                        else:
                            booking = ""  
                            booking_2 = ""
                    else:
                        if gdpr_status not in ["false"]:
                            booking = reschedule_cancel_booking_instructions
                            booking_2 = reschedule_instructions_rules_important
                        else:
                            booking = ""  
                            booking_2 = ""
                else:
                    booking = location_instructions_rules
                    booking_2 = ""
            else:
                if not request_data.flagBooked:
                    booking = ""
                    booking_2 = ""
                    lead_rules = lead_instructions_rule
                 

            tz = timezone.utc
            if request_data.client_details.get("timezone"):
                try:
                    tz = pytz.timezone(request_data.client_details.get("timezone"))
                except Exception as e:
                    tz = timezone.utc
            
            current_utc = datetime.now(tz)
            formatted_date = current_utc.strftime("%A, %B %d, %Y")
            formatted_time = current_utc.strftime("%H:%M:%S")
            formatted_day = current_utc.strftime("%A")
    
            if request_data.stream in ["True", True, "true"]:
                for chunk in agent_with_chat_history.stream(
                    {
                    'query':request_data.query,
                    'tool_names':tool_names,
                    "metadata":request_data.metadata,
                    "details":request_data.client_details,
                    "chatbot_name":request_data.chatbot_name,
                    "org_name":request_data.org_name,
                    "booking_tour_fields":request_data.booking_tour_fields,
                    "gated_or_transparent_instructions": instruction ,
                    "branch_name":request_data.client_details.get("branch_name") or None,
                    "branch_address":request_data.client_details.get("branch_address") or None,
                    "booking_instructions":booking,
                    "booking_instructions_2":booking_2,
                    "Time": formatted_time,
                    "Today": formatted_date,
                "Day": formatted_day,
                   "important": important_prompt,
                   "lead_rules": lead_rules,
                   "flagBooked": request_data.flagBooked
                    },config=config):
                        pass
            else:
                generated_response = await agent_with_chat_history.ainvoke(
                {
                    'query':request_data.query,
                   'tool_names':tool_names,
                   "metadata":request_data.metadata,
                   "details":request_data.client_details,
                   "chatbot_name":request_data.chatbot_name,
                   "org_name":request_data.org_name,
                   "booking_tour_fields":request_data.booking_tour_fields,
                   "gated_or_transparent_instructions": instruction ,
                   "branch_name":request_data.client_details.get("branch_name") or None,
                   "branch_address":request_data.client_details.get("branch_address") or None,
                   "booking_instructions":booking,
                   "booking_instructions_2":booking_2,
                   "Time": formatted_time,
                "Today": formatted_date,
                "today": formatted_date,
                "bookedFlag": request_data.flagBooked or None,
                "Day": formatted_day,
                   "important": important_prompt,
                   "lead_rules": lead_rules,
                    "flagBooked": request_data.flagBooked or None
                 },config=config)
                resp = generated_response.get('output')
                time2= datetime.now()
                diff_time=time2-time1
                if  request_data.WantsLocation:
                     return {"result":resp,'sender':request_data.actual_sender,'response_time':diff_time, "query": request_data.query, "branchSelection": True}, request_data.unhandled_arguments, request_data.user_intent,request_data.sessionExists, request_data.tourBooked
                return {"result":resp,'sender':request_data.actual_sender,'response_time':diff_time, "Tool Used?":request_data.toolinvoked, "Language Required": request_data.requiredLanguage}, request_data.unhandled_arguments, request_data.user_intent, request_data.sessionExists, request_data.tourBooked
            