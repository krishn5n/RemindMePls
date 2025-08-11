from __future__ import print_function
import os.path
import base64
import re
import psycopg2
from dotenv import load_dotenv
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import pubsub_v1
from google.oauth2 import service_account

load_dotenv()

class GmailUser:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("USER_DB_HOST",""),
            database=os.getenv("USER_DB_NAME",""),
            user=os.getenv("USER_DB_USER",""),
            password=os.getenv("USER_DB_PASSWORD",""),
            port=os.getenv("USER_DB_PORT","")
        )
        self.cursor = self.conn.cursor()
        self.app_creds = {}
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']

        self.app_creds["web"] = {}
        self.app_creds["web"]['client_id'] = os.getenv("client_id".upper(),"")
        self.app_creds["web"]['project_id'] = os.getenv("project_id".upper(),"")
        self.app_creds["web"]['auth_uri'] = os.getenv("auth_uri".upper(),"")
        self.app_creds["web"]['token_uri'] = os.getenv("token_uri".upper(),"")
        self.app_creds["web"]['auth_provider_x509_cert_url'] = os.getenv("auth_provider_x509_cert_url".upper(),"")
        self.app_creds["web"]['client_secret'] = os.getenv("client_secret".upper(),"")
        self.app_creds["web"]['redirect_uris'] = os.getenv("redirect_uris".upper(),"")
        self.app_creds["web"]['javascript_origins'] = os.getenv("javascript_origins".upper(),"")

        self.PROJECT_ID = os.getenv("PROJECT_ID","")
        self.SUBSCRIPTION_ID = "gmail-subscription"

        self.creds_info ={}
        vals = ["TYPE","PROJECT_ID","PIVATE_KEY_ID","PRIVATE_KEY","CLIENT_EMAIL","CLIENT_ID","AUTH_URI","TOKEN_URI","AUTH_PROVIDER_X509_CERT_URL","CLIENT_X509_CERT_URL","UNIVERSE_DOMAIN"]

        for i in vals:
            self.creds_info[i.lower()] = os.getenv("GCP_"+i)
        credentials = service_account.Credentials.from_service_account_info(self.creds_info)
        self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

    def user(self,email):
        try:
            print(email)
            creds = None
            if not email:
                return 400
            creds_dict = self.load_creds(email)
            creds = None
            if creds_dict:
                creds = Credentials.from_authorized_user_info(creds_dict, self.scopes)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self.save_creds(email,creds.to_json())
                else:
                    flow = InstalledAppFlow.from_client_config(self.app_creds, self.scopes)
                    creds = flow.run_local_server(port=3000)
                    watch_request = {
                        "labelIds": ["INBOX"],
                        "topicName": "projects/remindmepls/topics/RemindMePls"
                    }
                    service = build('gmail', 'v1', credentials=creds)
                    watch_response = service.users().watch(userId='me', body=watch_request).execute()
                    self.add_creds(email,creds)
                    if not watch_response:
                        raise Exception("Error in the watch_response for",e)
            return 200
        except Exception as e:
            print(e)
    
    def start_subscriber(self):
        subscription_path = self.subscriber.subscription_path(self.PROJECT_ID, self.SUBSCRIPTION_ID)
        streaming_pull_future = self.subscriber.subscribe(subscription_path, callback=self._callback)
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()

    def _callback(self,payload):
        data = json.loads(payload.data.decode("utf-8"))
        print(data)

    def load_creds(self,email):
        try:
            self.cursor.execute("Select * from gmail_users where email=%s",(email,))
            print("Load la irukkenn")
            ans = self.cursor.fetchone()
            print("Answer is",ans)
            if not ans == 0:
                return {}
            jsonbval = ans[3]
            if isinstance(jsonbval, str):
                creds_dict = json.loads(jsonbval)  # Convert string to dict
                return creds_dict
            return jsonbval
        except Exception as e:
            print("Load credits Error",e)
    def add_creds(self,email,creds,number):
        try:
            jsonval = json.dumps(json.loads(creds.to_json()))
            self.cursor.execute("INSERT INTO gmail_users (email, phone_number, credentials_json) VALUES (%s, %s, %s);", (email, number, jsonval))
            self.conn.commit()
        except Exception as e:
            print("Add credits Error",e)
        return
    def save_creds(self,email,creds):
        try:
            jsonval = json.dumps(json.loads(creds.to_json()))
            self.cursor.execute("UPDATE gmail_users SET credentials_json=%s where email=%s",jsonval,email)
            self.conn.commit()
            return
        except Exception as e:
            print("Save credits Error",e)
    def close(self):
        self.cursor.close()
        self.conn.close()
