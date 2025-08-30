from __future__ import print_function
import time
import asyncio
from sqlalchemy import text
import os.path
import random
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
from models import User
from base64 import urlsafe_b64decode
from google.auth.transport.requests import Request
from sqlalchemy import create_engine, text
import redis

from AI import ProcessMail

load_dotenv()


#A Parent Class to Enforce Token Usage
class Tokens:
    def __init__(self,user:User=None):

        self.app_creds = {}
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        self.user = user
        self.app_creds["web"] = {}
        appcred = ["client_id","project_id","auth_uri","token_uri","auth_provider_x509_cert_url","client_secret","redirect_uris","javascript_origins"]
        for i in appcred:
            newval = i.upper()
            self.app_creds["web"][i] = os.getenv(newval,"")
        
        '''Database Related-----------------------------------------------------------------------------------------------------------------'''
        DATABASE_URL = f"postgresql+psycopg2://{os.getenv("USER_DB_USER","")}:{os.getenv("USER_DB_PASSWORD","")}@{os.getenv("USER_DB_HOST","")}:5432/{os.getenv("USER_DB_NAME","")}"
        self.engine = create_engine(
            DATABASE_URL,
            pool_size=50,        # number of connections kept open
            max_overflow=20,     # extra connections allowed above pool_size
            pool_timeout=30,     # wait time (in seconds) before giving up
            pool_recycle=1800,   # recycle connections every 30 min (avoid stale)
            pool_pre_ping=True   # check if connection is alive before using
        )


        ''' Access credentials for the Application OAuth Gateway ----------------------------------------------------------------------------'''
        self.creds_info ={}
        vals = ["TYPE","PROJECT_ID","PRIVATE_KEY_ID","PRIVATE_KEY","CLIENT_EMAIL","CLIENT_ID","AUTH_URI","TOKEN_URI","AUTH_PROVIDER_X509_CERT_URL","CLIENT_X509_CERT_URL","UNIVERSE_DOMAIN"]
        for i in vals:
            self.creds_info[i.lower()] = os.getenv("GCP_"+i)
        credentials = service_account.Credentials.from_service_account_info(self.creds_info)

        ''' Subscriber Post -----------------------------------------------------------------------------------------------------------------'''
        self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        self.PROJECT_ID = os.getenv("PROJECT_ID","")
        self.SUBSCRIPTION_ID = "gmail-subscription"

        '''Redis Related-----------------------------------------------------------------------------------------------------------------'''
        self.redis_key = 'processed_emails'
        self.redis = redis.Redis(
            host=os.getenv("REDIS_URL",""),
            port = os.getenv("REDIS_PORT",""),
            username=os.getenv("REDIS_NAME",""),
            password=os.getenv("REDIS_PASSWORD","")
        )

    def create_user(self):
        try:
            user = self.user
            creds = None
            if not user.email:
                return 400
            creds = self.authentication(user)
            if not creds:
                raise Exception("Error in the create user for creds being empty from auth")
            return 200
        except Exception as e:
            print(e)
    
    #Authentication -> Authenticate User on board
    def authentication(self,user:User):
        try:
            flow = InstalledAppFlow.from_client_config(self.app_creds, self.scopes)
            creds = flow.run_local_server(port=3000,prompt="consent") #Stores the Refresh Token for Onboarding

            self.add_creds(user, creds)
            self.watch_connection(user.email)
            return creds
        except Exception as e:
            print(f"Exception at authenticate_user {e}")
            return None

    #Watch -> Publish user to renew or setup connection to pub/sub
    def watch_connection(self,email:str):
        try:
            creds = self.refresh(email)

            watch_request = {
                "labelIds": ["INBOX"],
                "topicName": "projects/remindmepls/topics/RemindMePls"
            }

            service = build('gmail', 'v1', credentials=creds)
            watch_response = service.users().watch(
                userId=email,
                body=watch_request
            ).execute()
            self.update_response(history=watch_response["historyId"],email=email)
            return 
        except Exception as e:
            print(f"Exception at renew_watch {e}")
            return 


    #To Get or Refresh Access Tokens
    def refresh(self,email:str):
        try:
            creds_dict = self.load_creds(email)
            creds = None
            if creds_dict:
                creds = Credentials.from_authorized_user_info(creds_dict, self.scopes)

            if creds and not creds.expired:
                return creds
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            print("Error at refreshing tokens",e)
    
    #To obtain the user model
    def get_user_model(self,email:str):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("Select * from users where email=:email"),
                    [{"email":email}]
                )
                ans = result.fetchone()
                if not ans or len(ans) == 0:
                    return None
                user = User(email=email,phone=int(ans[3]),cgpa=float(ans[5]),regno=ans[2])
                return user
        except Exception as e:
            print("User Model Conversion error",e)
            return None
    '''---------------------------------------------------------------------------------------
    ---------------------------------------------------------------------------------------
    ---------------------------------------------------------------------------------------
    Credentials Related
    '''

    def load_creds(self,email:str):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("Select * from users where email=:email"),
                    [{"email":email}]
                )
                ans = result.fetchone()
                if not ans or len(ans) == 0:
                    return {}
                jsonbval = ans[4]
                if not jsonbval:
                    return {}
                if isinstance(jsonbval, str):
                    creds_dict = json.loads(jsonbval)
                    return creds_dict
                return jsonbval
        except Exception as e:
            print("Load credits Error",e)

    def add_creds(self,user:User,creds):
        try:
            with self.engine.begin() as conn:
                jsonval = json.dumps(json.loads(creds.to_json()))
                result = conn.execute(
                    text("INSERT INTO users (email, reg_number, phone_number,cgpa,credentials) VALUES (:email,:regno,:phone,:cgpa,:jsonval);"),
                    [{"email":user.email, "regno":user.regno,"phone":user.phone,"cgpa":user.cgpa, "jsonval":jsonval}]
                )
        except Exception as e:
            print("Add credits Error",e)

    def exist_user(self,email):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    text("SELECT EXISTS(SELECT 1 FROM users WHERE email = :email);"),
                    [{"email": email}]
                )
                ans = result.fetchone()[0]
                return ans
        except Exception as e:
            print("Update Watch response Error",e)
    
    def update_response(self,history,email):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    text("UPDATE users set prev_history=:history where email=:email;"),
                    [{"email": email, "history": history}]
                )
        except Exception as e:
            print("Update Watch response Error",e)


#Gmail Class for 
class Gmail(Tokens):    
    def start_subscriber(self):
        subscription_path = self.subscriber.subscription_path(self.PROJECT_ID, self.SUBSCRIPTION_ID)
        streaming_pull_future = self.subscriber.subscribe(subscription_path, callback=self.checkmail)
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
    
    #Callback Function for Pull Notifications
    def checkmail(self,payload):
        try:
            data = json.loads(payload.data.decode("utf-8"))
            email = data.get("emailAddress","")

            if not self.exist_user(email):
                return
            historyid = data.get("historyId","")
            history = self.get_history_mails(historyid,email)
            if not history:
                raise Exception("Obtained a new history ID that is smaller than prev")
            msg_id = self.extract_message_ids(history)
            # return
            print(msg_id)
            for unique_message_id in msg_id:
                # success = self.test(email,unique_message_id)

                obj = ProcessMail()
                creds = self.refresh(email)
                print(obj.get_message(message_id=unique_message_id,user_id=email,creds=creds))
            self.update_response(history=historyid,email=email)
            payload.ack()
        except Exception as e:
            # print("Error in the Checking Mail Callback",e)
            return 

    #Get History of Mails -> Since last watch
    def get_history_mails(self,historyId,email:str):
        try:
            last_history_id = self.get_start_history(email)
            if not last_history_id or int(last_history_id) > int(historyId):
                return None

            creds = self.refresh(email)
            service = build('gmail', 'v1', credentials=creds)

            response = service.users().history().list(
                userId=email,
                startHistoryId=last_history_id,
                historyTypes=["messageAdded"]
            ).execute()
            
            history = response.get("history", [])
            return history
        except Exception as e:
            print("Error has occured at Checkmail Function",e)
            return []

    #Unique Id's For each and every single msg given
    def extract_message_ids(self, history):
        try:
            message_ids = []
            for record in history:
                for msg in record.get("messagesAdded", []):
                    message_ids.append(msg["message"]["id"])
            return message_ids
        except Exception as e:
            print("There is some error in extracting message_id",e)
            return []
        
    def test(self,email,msgid):
        try:
            creds = self.refresh(email)
            service = build('gmail', 'v1', credentials=creds)
            response = service.users().messages().attachments().get(
                userId=email,
                messageId=msgid,

            )
        except Exception as e:
            print(f"An error occurred: {e}")
        

    #This function will be used for essentially having locks on the Mailid
    #Make this a call that continues to occur till you get a True -> Ensure
    async def handle_retry_mechanism(self,email,mailid):
        try:
            retrycnt = 3
            while retrycnt > 0:
                success = await self.handling_locking(email,mailid)
                if success: #Has processed
                    print("Finished handling of locks",email)
                    return True #Go and process
                
                time_to_sleep = random.randint(20,40)
                print("Sleeping now",email,time_to_sleep)
                await asyncio.sleep(time_to_sleep)
                retrycnt-=1
            print("Following mail id and email did not process",email,mailid)
            return False
        except Exception as e:
            print("Error occured at handle_retry_mechanism",e)
            return False

    async def handling_locking(self,email,mailid):
        try:
            if self.redis.sismember(self.redis_key, mailid):
                print(f"Email '{mailid}' has already been processed so leaving {email}.")
                return True
            lock_key = f"lock:{mailid}"
            lock_acquired = self.redis.set(lock_key, int(time.time()), nx=True, ex=120)
            if lock_acquired:
                try:
                    #Create a code to handle the processing
                    # self.handle_processing_mail(email,mailid)
                    print("Obtaining the lock and going to sleep",email,mailid)
                    await asyncio.sleep(30)
                    # await asyncio.to_thread(self.handle_cpu_intensive_processing, email, mailid)
                    print("Woke up and Adding the key",email,mailid)
                    self.redis.sadd(self.redis_key, mailid)
                    return True
                except Exception as e:
                    print("Error has occured in lock post acquiring",e)
                    return False
                finally:
                    print("Releasing Lock")
                    self.redis.delete(lock_key)
            else:
                print("Lock Not Acquired",email)
                return False
        except Exception as e:
            print("Error in handling Existance of Locks and Mailid",e)
            return False    

    '''Queries Related -------------------------------------------------------------------------'''
    '''-------------------------------------------------------------------------'''

    #Provide the latest history from watch the watch response
    def get_start_history(self,email:str):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("Select prev_history from users where email=:email;"),
                    [{"email":email}]
                )
                ans = result.fetchone()
                if not ans or len(ans) == 0:
                    return None
                return int(ans[0])
        except Exception as e:
            print("Error at the getting start history",e)

f'''
Flows
1. Authentication Flow                                                                      |=================================| => This Flow can be a separate flow done by calling watch() function with email
Create User -> (user model) -> Authentication -> (Get Credentials) -> Add Creds to db -> Refresh The Tokens -> Then Set up Watch Connection

2. Obtaining Mail
(History ID and Email) -> Callback -> Get The history post last seen history -> Get mail ID -> Obtain locks and see if processed -> If not processed then you process it -> If processed , get details from db and just send it

3. Setting up watch connection after every 7 days => Calling watch() with email -> Refreshing tokens


'''