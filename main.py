from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from models import User
import uvicorn

app = FastAPI()

from gmail import GmailUser


@asynccontextmanager
async def lifespan(app: FastAPI):
    def run_subscriber():
        gmail_service = GmailUser()
        gmail_service.start_subscriber()
    thread = threading.Thread(target=run_subscriber, daemon=True)
    thread.start()

@app.post("/users")
async def users(user:User):
    try:
        gmail_obj = GmailUser()
        status = gmail_obj.user(user.email)
        gmail_obj.close()
        return status
    except Exception as e:
        return 400

@app.get("/test")
async def test():
    print("Works")
    return

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# from __future__ import print_function
# import os.path
# import base64
# import re
# import psycopg2
# from dotenv import load_dotenv
# import json
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# load_dotenv()


# def main(email=None):
#     try:
#         creds = None
#         if not email:
#             return 400

#         creds_dict = load_creds(email)
#         creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
#         if not creds or not creds.valid:
#             if creds and creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#             else:
#                 flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
#                 creds = flow.run_local_server(port=3000)
#             save_creds(email,creds.to_json())

#         service = build('gmail', 'v1', credentials=creds)
#         results = service.users().messages().list(userId='me', maxResults=5).execute()
#         messages = results.get('messages', [])

#         if not messages:
#             print("No messages found.")
#         else:
#             print("Recent messages:")
#             for msg in messages:
#                 msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
#                 snippet = msg_data['snippet']
#                 print(f"- {snippet}")
#     except Exception as e:
#         print(e)


# def load_creds(email):
#     conn = psycopg2.connect(
#         host=os.getenv("USER_DB_HOST",""),
#         database=os.getenv("USER_DB_NAME",""),
#         user=os.getenv("USER_DB_USER",""),
#         password=os.getenv("USER_DB_PASSWORD",""),
#         port=os.getenv("USER_DB_PORT","")
#     )
#     cursor = conn.cursor()
#     query = f"Select * from gmail_users where email={email}"
#     cursor.execute(query)
#     ans = cursor.fetchone()
#     if len(ans) == 0:
#         return {}
#     jsonbval = ans[3]
#     cursor.close()
#     conn.close()
#     if isinstance(jsonbval, str):
#         creds_dict = json.loads(jsonbval)  # Convert string to dict
#         return creds_dict
#     return jsonbval

# def save_creds(email,creds):
#     conn = psycopg2.connect(
#         host=os.getenv("USER_DB_HOST",""),
#         database=os.getenv("USER_DB_NAME",""),
#         user=os.getenv("USER_DB_USER",""),
#         password=os.getenv("USER_DB_PASSWORD",""),
#         port=os.getenv("USER_DB_PORT","")
#     )
#     cursor = conn.cursor()
#     query = f"UPDATE gmail_users SET credentials_json={json.dumps(json.loads(creds.to_json()))} where email={email}"
#     cursor.execute(query)
#     conn.commit()
#     cursor.close()
#     conn.close()
#     return


# def test():
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("USER_DB_HOST",""),
#             database=os.getenv("USER_DB_NAME",""),
#             user=os.getenv("USER_DB_USER",""),
#             password=os.getenv("USER_DB_PASSWORD",""),
#             port=os.getenv("USER_DB_PORT","")
#         )

#         cursor = conn.cursor()
#         cursor.execute("Select * from gmail_users")
#         res = cursor.fetchall()
#     except Exception as e:
#         print(e)

# if __name__ == '__main__':
#     test()