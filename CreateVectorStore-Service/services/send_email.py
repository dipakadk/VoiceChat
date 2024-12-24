import email.message
import smtplib
import os;
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from icalendar import Calendar, Event, vCalAddress
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from dateutil import parser
from email.mime.base import MIMEBase
from email import encoders
from email_template import email_template
from email.utils import formataddr

load_dotenv(find_dotenv())
EMAIL_PASSWORD= os.getenv('EMAIL_PASSWORD')
EMAIL= os.getenv('EMAIL')
SMTP_HOST= os.getenv('SMTP_HOST')
SMTP_PORT= os.getenv('SMTP_PORT')
TO_EMAIL= os.getenv('SEND_EMAIL')
SERVER_BASE_URL= os.getenv('SERVER_BASE_URL')

def sendCustomEmailAttachments(CONTENT, SUBJECT, ATTACHMENT_PATH, TO_EMAIL=TO_EMAIL):
    try:
        
        message = MIMEMultipart()
        message["From"] = formataddr(("Keepme Fit Club", EMAIL))
        message["To"] = TO_EMAIL
        message["Subject"] = SUBJECT

        
        message.attach(MIMEText(CONTENT, "html"))

        
        if ATTACHMENT_PATH:
            print("ATTACHMENT PATH", ATTACHMENT_PATH)
            for k in ATTACHMENT_PATH:
                print("File ", k)
                try:
                    with open(k, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())

                    
                    if not isinstance(part.get_payload(decode=True), (bytes, bytearray)):
                        raise ValueError("Payload is not in binary format")

                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {os.path.basename(k)}",
                    )
                    message.attach(part)
                except FileNotFoundError:
                    print(f"Attachment {k} not found. Skipping this file.")
                except Exception as e:
                    print(f"Could not attach file {k}. Error: {e}")

        # Connect to the server and send the email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            server.send_message(message)

        print("Successfully sent")
    except Exception as ex:
        print("Something went wrong....", ex)

def sendCustomEmail(CONTENT,SUBJECT,TO_EMAIL=TO_EMAIL):
    try: 
        msg = email.message.Message()
        msg['Subject'] = f'{SUBJECT}'
        msg['From'] = formataddr(("Keepme Fit Club", EMAIL))
        msg['To'] = TO_EMAIL
        msg.add_header('Content-Type','text/html')
        msg.set_payload(f'{CONTENT}')

        smtp = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtp.starttls()
        smtp.login(EMAIL,EMAIL_PASSWORD)
        smtp.sendmail(msg['From'], [msg['To']], msg.as_string())
        smtp.quit()
        print("Succesfully send")
    except Exception as ex: 
        print("Something went wrong....",ex)

def sendCalanderEvents(events_data=None):
    print("event type",type(events_data))
    print(events_data)
    cal = Calendar()
    event = Event()
    event.add('summary', 'Tour Booking Confirmation')
    print("before time")
    event.add('dtstart',parser.isoparse(events_data.get('startTime')))
    event.add('dtend',parser.isoparse(events_data.get('endtime')))
    # event.add('dtstart',datetime.now())
    # event.add('dtend',datetime.now())
    print(type(datetime.now()))
    event.add('description', events_data.get('description'))
    event.add('location', events_data.get('location'))
    # Add organizer
    organizer = vCalAddress("mailto:olivia@keepmefit.club")
    organizer.params['cn'] = 'Olivia'
    event.add('organizer', organizer)

    cal.add_component(event)

    ical_string = cal.to_ical().decode('utf-8')
    # confirmation_token = create_access_token(events_data)
    # confirmation_url = f"{CONFIRMATION_BASE_URL}?token={confirmation_token}"

    msg = MIMEMultipart()
    msg['From'] = formataddr(("Keepme Fit Club", EMAIL))
    msg['To'] = events_data.get('emailAddress') or TO_EMAIL
    msg['Subject'] = 'Tour Booking Confirmation'

    # Email body
    body = email_template(events_data.get("first_name"),events_data.get("date"),events_data.get("time"))
    msg.attach(MIMEText(body, 'html'))


    # Attach the .ics file
    attachment = MIMEText(ical_string, 'calendar', 'utf-8')
    attachment.add_header('Content-Disposition', 'attachment', filename='invitation.ics')
    msg.attach(attachment)

    # Send email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)

    print('Message  has been sent.')