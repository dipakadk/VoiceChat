from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap

template = """
You are a professional intent classifier for Gym and you only speak json. 
You need to classify current query of the user along with the previous conversation history and analyze the intent of the user.
Here is the current user query in double backticks: ``{query}``
Here is the previous conversation in triple backticks: ```{history}```.
Here are the following intents you need to classify the user query into:
1. general: If the user query and conversation aligns with the general information of the gym like membership plans, prices and etc. Also includes general normal conversation with the gym sales agent.
2. booking: If the user query and conversation aligns with the user trying to book the tour/classes/trial/visits/pass.
3. reschedule: If the user query and conversation aligns with the user trying to reschedule the booked tour/classes/visits/pass.
4. cancel: If the user query and conversation align with the user trying to cancel the booked tour/classes/visits/pass.
Your output must be in json format as 
dict(
"intent" : "Only Name of the intent without any additional texts or backticks."
)
remember that dict refers to curly brackets.
"""



def classify_intent(query:str, metadata:dict, history, llm):
    prompt = ChatPromptTemplate.from_template(template=template)
    chain = RunnableMap(
        {
            "query": lambda x: x["query"],
            "history": lambda x: x["history"]
        }
    ) | prompt | llm | JsonOutputParser()

    json_response = chain.invoke({"query": query, "history": history})

    return json_response

