from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from models import User
import asyncio
import uvicorn


from gmail import Tokens,Gmail


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
        gmail_obj.close()
        print("Finished")
        return status
    except Exception as e:
        print(f"There is error {e}")
        return 400

@app.get("/test")
async def test():
    print("Works")
    return

@app.get("/call_watch")
async def watch():
    return


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
