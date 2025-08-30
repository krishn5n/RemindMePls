from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from models import User
import asyncio
import uvicorn

from gmail import Gmail


def run_subscriber():
    user = None
    gmail_obj = Gmail(user)
    gmail_obj.start_subscriber()

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=run_subscriber, daemon=True)
    thread.start()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/users")
async def users(user:User):
    try:
        print("Inside the path",user)
        gmail_obj = Gmail(user)
        status = gmail_obj.create_user()
        print("Finished")
        return status
    except Exception as e:
        print(f"There is error {e}")
        return 400

@app.post("/test")
async def test(user:User):
    try:
        gmail_obj = Gmail(user)
        process = False
        print(user.email,"Arrived")

        if user.cgpa > 9.00:
            process = await gmail_obj.handle_retry_mechanism(user.email,2)
        else:            
            await asyncio.sleep(5)
            print("Now going",user.email)
            process = await gmail_obj.handle_retry_mechanism(user.email,2)

        print("Finished",user.email,process)
        # # gmail_obj.test()
        # gmail_obj.cleanup_duplicate_subscriptions(user.email)
        return 200
    except Exception as e:
        print(f"There is error {e}")
        return 400

@app.get("/call_watch")
async def watch():
    return


#To remove subscription
@app.get("/remove")
async def remove():
    return

@app.get("/cron")
async def cron():
    return 


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
