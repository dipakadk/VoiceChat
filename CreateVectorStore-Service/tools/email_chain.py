from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_core.runnables import RunnableMap
import os
from services.send_email import sendCustomEmailAttachments
from services.http_api import http_post

def send_email_tool(self):
    def email_response(query:str, email:str):
        template = """
        You are provided with a query in double backticks.
        You are provided with conversation history that contains necessary details that needs to be re formatted in the email format.
        Analyze the history and add what information needs to be added in the email message.
        add footer as warm regards, Olivia. Add necessary introduction message as Hi, name of the user which can be found in the history conversation.
        Then add the body message for which the mail is being written looking at the conversation history. 
        ## Query : ``{query}``
        ## chat_history: ```{chat_history}````
        Your task is to generate a json output without any extra tags or backticks. 
        The required format is as follows:
        dict(
        "title":"subject of the email, make it appropriate"
        "response":"Your response should be only regarding here is the attachment regarding what details they need with needed footer, nothing else. in proper html format",
        "reply":"message stating that mail has been sent to email address name, make it appropriate"
        )  
        Reminder that dict refers to curly brackets.
        """

        email_prompt = ChatPromptTemplate.from_template(template=template)
        chain=email_prompt | self.llm | JsonOutputParser()

        agent_with_chat_history = RunnableWithMessageHistory(
                    chain,
                    lambda session_id: self.history,
                    input_messages_key="query",
                    history_messages_key="chat_history",
                    verbose=True
                )
        

        if email :
            config = {"configurable": {"session_id": self.sender}}
            json_response= agent_with_chat_history.invoke({'query':query}, config=config)
            print("JSON REPLY------------------------------------------",json_response)
            json_response1 = classify_intents(query)
            intents = json_response1.get("intents")
            attachments_path = None
            if intents != [None]:
                attachments_path = [os.path.join("Attachments", k) for k in intents]
            email_message = json_response.get("response")
            reply = json_response.get("reply")
            title = json_response.get("title")
            sendCustomEmailAttachments(email_message, title, attachments_path,email)
            return reply
    

    
    def classify_intents(query:str):
        intent_template = """Here is the query provided in double backticks that includes trying to send email about a certain topic:
        ### User query: ``{query}``
        Your task is to classify the intent of this query's topic into some of the provided categories.
        "class_schedule.pdf": If the topic of the query is regarding the class timings and schedule of the gym.
        "code_of_conduct.pdf": If the topic of the query is regarding violaions, code of conducts, of the gym.
        "dignity.pdf": If the topic of the query is regarding the dignity of the gym.
        "gym_rules.pdf": If the topic of the query is regarding the rules of the gym.
        "membership_details.pdf": If the topic of the query is regarding the membership details, plans of the gym.
        "responsibilities.pdf": If the topic of the query is regarding the responsibilities of the gym, trainers, etc.
        "signup_detail.pdf": If the topic of the query is regarding the signup details of the gym, etc.
        Your response must be in a json format in the provided format like:
        dict(
        "intents": ["name of the intent classified"]
        )
        If you cannot classify any of the categories if the query, just provide 
        dict(
        "intents": [None]
        )
        Do not add any additional texts or phrases in your output. Do not add any backticks. Just provide the json output.
        """

        intent_prompt = ChatPromptTemplate.from_template(intent_template)

        intent_chain = RunnableMap(
            {
                "query": lambda x: x["query"]
            }
        ) | intent_prompt | self.llm | JsonOutputParser()

        return intent_chain.invoke({
            "query":query
        })


    return email_response




