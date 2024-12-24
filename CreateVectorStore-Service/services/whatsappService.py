from db.db_config import messages_collection
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap
import os
from fastapi import HTTPException
from dotenv import load_dotenv, find_dotenv
import requests
from utils.redis_whatsapp import setData, getData
from urllib.parse import urlencode, urljoin

load_dotenv(find_dotenv())

keepme_url = os.getenv("KEEP_ME_URL")


template = """
Your task is to analyze the user query provided within double backticks: ``{query}``, which is a response to the message inside triple backticks ```{response}```. You have a mapping of data items under four backticks ````{data}````, where each item has an ID [1,2,3...]. Analyze the user query to determine which location they are selecting. Respond strictly in this JSON format:
dict(
"id": "The corresponding ID from the data of which the user is trying to choose the location of. Keep it strictly as 'none' if you cannot analyze which location is trying to contact to."
)
Do not add any additional backticks or texts in your json response.
Reminder that dict refers to curly brackets.
You must always return valid JSON format with field "id". Do not add any additional texts or word dict() in your response.
"""


def buildUrl(base_url, endpoint, queryParams):
    url = urljoin(base_url, endpoint)
    query = urlencode(queryParams, safe=":+")
    return f"{url}?{query}"



async def findInitialMessage(sender:str, whatsapp_number:str):
    query_search = {"sender": sender, "whatsapp_number":whatsapp_number}
    projection = {"_id": 0, "initialFlag":1, "ai_message": 1}

    result = await messages_collection.find(query_search, projection).sort("updated_date",-1).limit(1).to_list(length=1)

    if result:
        return result[0]
    return None

async def searchVisitorBySender(sender:str,llm, query:str = None, organization_id:str=None, region_id:str=None, whatsapp_number:str=None, agent:str=None):
    try:
        base_url = keepme_url
        endpoint = "/api/branches/branches-list"
        
        query_params = {}
        if whatsapp_number:
            query_params["whatsapp"] = whatsapp_number
        elif region_id:
            query_params["region"] = region_id
        elif organization_id:
            query_params["client"] = organization_id

        
        url = buildUrl(base_url, endpoint, query_params)
        print("url is==============",url)
        headers = {
            "apikey": "12345",
                "Content-Type": "application/json"
        }
        response = requests.get(url=url, headers=headers)  
        response = response.json()  
        # print("response==================",response)       
        if not response or "data" not in response:
            raise HTTPException(status_code=400, detail=f"No data found in the external API response. for {url}")
        else:
            status = getData(f"{sender}_{whatsapp_number}_status") or None

            print("Status is=======================",status)

            
            if not getData(f"{sender}_{whatsapp_number}_firstQuery"):
                setData(f"{sender}_{whatsapp_number}_firstQuery", str(query))


            print("First Query is=======================",getData(f"{sender}_{whatsapp_number}_firstQuery"))


            data = response.get("data", {})
            client_name = data[0]['name']
            clientid = data[0]['client']['_id']
            branches = [{"ID": branch_info['branch']['_id'], "name": branch_info['branch']['name']}for branch_info in data]
            branches = list({branch['ID']: branch for branch in branches}.values())
            if len(branches) == 1:
                return {"branch": branches[0]["ID"], "oldQuery": query or "Hello", "organization_id": clientid}
            message = f"Hi, I am {client_name}, your virtual assistant. Please choose a location for detailed information about our club's services.\n\n"

            for index, branch in enumerate(branches):
                message += f"Type {index+1} for {branch['name']}\n"
                setData(f"{sender}_{whatsapp_number}_branchNumber_{index+1}_id", str(branch["ID"]))
            if not status:
                setData(f"{sender}_{whatsapp_number}_message", str(message))
                setData(f"{sender}_{whatsapp_number}_status", "completed")
                return message
            else:
                numberOfBranches = len(branches)
                branches_data = {}
                for index in range(numberOfBranches):
                    branches_data[f"{index+1}"] = getData(f"{sender}_{whatsapp_number}_branchNumber_{index+1}_id")


                prompt = ChatPromptTemplate.from_template(template)

                chain = RunnableMap(
                    {
                        "query": lambda x: x["query"],
                        "response": lambda x: x["response"],
                        "data": lambda x: x["data"]
                    }
                ) | prompt | llm | JsonOutputParser()

                print("User query is===========",query)

                json_response = await chain.ainvoke({"query": query, "response": message, "data":branches_data})

                print("Json response is===========================",json_response)

                id = json_response.get("id")

                if id in ["none", "None", None, "'none'"]:
                    return message
                else:
                    setData(f"{sender}_{whatsapp_number}_status",None)
                    firstQuery = getData(f"{sender}_{whatsapp_number}_firstQuery")
                    setData("{sender}_{whatsapp_number}_firstQuery", None)
                    setData("{sender}_{whatsapp_number}_message", None)
                    return {"branch": id, "oldQuery": firstQuery or "Hello", "organization_id": clientid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
