from twilio.rest import Client
import os;
from dotenv import load_dotenv, find_dotenv
import json

load_dotenv(find_dotenv())




#twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER=os.getenv('TWILIO_FROM_NUMBER')
MESSAGING_SERVICE_SID=os.getenv('MESSAGING_SERVICE_SID')
CONTENT_SID=os.getenv('CONTENT_SID')
COUNTRY_CODE = os.getenv("COUNTRY_CODE")



client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Function to send WhatsApp message
def send_whatsapp_message(data):
    try:
        first_name=data.get('first_name')
        start_date=data.get('date')
        start_time=data.get('time') 
        to=data.get('phone_number')
        message=data.get('message')
        
        message = client.messages.create(
            content_sid=CONTENT_SID,
            from_=TWILIO_FROM_NUMBER,
            content_variables=json.dumps({"1": f"{first_name}", "2": f"{start_date}", "3": f"{start_time}"}),
            messaging_service_sid=MESSAGING_SERVICE_SID,
            to="whatsapp:"+to
        )
        print("\n\n===========",message.body,"=====================send whatsapp message====\n\n")
    except Exception as e:
        print(f"Error: {e}")

