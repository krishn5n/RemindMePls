from multiprocessing import process
from dotenv import load_dotenv
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from models import User
from base64 import urlsafe_b64decode
from google.auth.transport.requests import Request
import base64
from io import BytesIO
import pandas as pd

load_dotenv()

class ProcessMail:
    def __init__(self):
        self.api = os.getenv("GEMINI_API_KEY","")
        self.excelType = {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.openxmlformats-officedocument.spreadsheetml.template',  # .xltx
            'application/vnd.ms-excel',  # .xls
            'application/msexcel',  # .xls variants
            'application/x-msexcel',
            'application/x-ms-excel',
            'application/x-excel'
        }        # self.client = genai.Client()

    def process_message(self,message_id,email):
        msg = self.get_message(message_id,email)

    #Obtaining Messages
    def get_message(self, message_id, user_id,creds):
        try:
            service = build('gmail', 'v1', credentials=creds)
            msg = service.users().messages().get(
                userId=user_id,
                id=message_id,
                format="full"
            ).execute()
            self.parse_message(msg,message_id,user_id,service)
            return msg
        except Exception as e:
            print(f"Error getting message: {e}")
            return None

    #Parsing Messages
    def parse_message(self, msg,msgid,emailid,service):
        subject = None
        body = None
        fromaddr = ""

        # Extract subject from headers
        for header in msg["payload"]["headers"]:
            if header["name"].lower() == "subject": 
                subject = header["value"]
            elif header["name"].lower() == "from":
                fromaddr = header["value"]

        # Extract body from payload
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                #Mime Type Can be
                    #Text/Plain
                    #application/pdf -> attache

                if part["mimeType"] == "text/plain":
                    body = urlsafe_b64decode(
                        part["body"]["data"].encode("UTF-8")
                    ).decode("UTF-8")
                    break
                elif part["mimeType"] in self.excelType:
                    if "body" in part and "attachmentId" in part["body"]:
                        self.process_excel_attachment(service,msgid,part["body"]["attachmendId"])
        else:
            # Sometimes the body is directly in payload
            body = urlsafe_b64decode(
                msg["payload"]["body"]["data"].encode("UTF-8")
            ).decode("UTF-8")

        return (subject, body)
    
    def process_excel_attachment(self, service, message_id, attachment_id):
        # Get the attachment
        attachment = service.users().messages().attachments().get(
            userId='me', 
            messageId=message_id, 
            id=attachment_id
        ).execute()
        
        # Decode and convert to pandas
        file_data = base64.urlsafe_b64decode(attachment['data'])
        excel_file = BytesIO(file_data)
        
        # Read into pandas DataFrame
        df = pd.read_excel(excel_file)
        print(df.info())

    def AIProcessing(self):
        pass

    def ManualProcessing(self):
        pass

'''
Attachment ID -> msg["payloads"]["parts"] -> Part in that -> Adhu mimeType is application/pdf -> adhu body -> attachmentId
    for part in msg["payloads"]["parts"]:
        if mimeType in part and part["mimeType"]  == "application/pdf":
            if body in part and attachmentId in part["body]:
                attachmentid = part["body"]["attachmentId"]
'''