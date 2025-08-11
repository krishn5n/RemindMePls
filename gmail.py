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
        self.final_app_creds = json.loads(self.app_creds)
    def load_creds(self,email):
        self.cursor.execute("Select * from gmail_users where email=%s",(email))
        ans = self.cursor.fetchone()
        if len(ans) == 0:
            return {}
        jsonbval = ans[3]
        if isinstance(jsonbval, str):
            creds_dict = json.loads(jsonbval)  # Convert string to dict
            return creds_dict
        return jsonbval
    def save_creds(self,email,creds):
        jsonval = json.dumps(json.loads(creds.to_json()))
        self.cursor.execute("UPDATE gmail_users SET credentials_json=%s where email=%s",jsonval,email)
        self.conn.commit()
        return
    def checkifplacemail():
        pass
    def getmoredetails():
        pass
    def close(self):
        self.cursor.close()
        self.conn.close()
