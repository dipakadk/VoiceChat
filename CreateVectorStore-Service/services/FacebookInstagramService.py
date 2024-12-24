import html2text
from utils.redis_whatsapp import getData, setData
from services.http_api import get_branch_details_from_orgid


from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os

SESSION_EXPIRE_TIME = os.getenv("SESSION_EXPIRE_TIME") or 7200

async def get_initial_case_facebookInstagram(request):

    async def convert_to_markdown(message):
        markdown_converter = html2text.HTML2Text()
        return markdown_converter.handle(message)

    agent = request.agent.lower()
    redis_key = f"{request.sender}_{request.org_id}_{agent}_new_field_{agent}"
    

    if request.query in ["/clear_2hr"]:
        setData(redis_key,None)
    
    redis_value = getData(redis_key) or None

    


    # print("request is========================",request)
    # print("region id is==================",request.region)
    if request.region_id is not None:
        if (redis_value is None or request.query in ["/select:branch"] ) :
            if not request.branch:
                markdown_text = await convert_to_markdown(request.welcome_message)
            else:
                regionid = request.details.get("branch", {}).get("region", None)
                if not regionid:
                    markdown_text = ""
                else:
                    details = await get_branch_details_from_orgid(org_id=request.org_id, branch_id=None, region_id=regionid)
                    welcome_message = details.get("data", {}).get("welcomeMessage", "")
                    markdown_text = await convert_to_markdown(welcome_message)
            
            setData(redis_key, "Set", int(SESSION_EXPIRE_TIME))
            print(f"Entered {agent.capitalize()} Initial Case")
            return {
                    "result": f"{markdown_text} Please Select the Club",
                    "sender": request.sender,
                    'response_time': "",
                    "query": "Hi",
                    "initialCase": True
                }
        else:
            return None
    else:
        if request.query in ["/select:branch"]:
            markdown_text = await convert_to_markdown (request.welcome_message)
            return {"result": markdown_text, "query": request.sender, "response_time": ""}
        else:
            return None


