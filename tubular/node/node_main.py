from tubular.node.node_state import NodeState

from fastapi import FastAPI
from contextlib import asynccontextmanager

NODE_STATE = NodeState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    NODE_STATE.start()
    yield
    NODE_STATE.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/status")
async def getStatus():
    return {
        "status": NODE_STATE.status.name,
        "tasks": NODE_STATE.taskQueue,
    }


@app.post("/queue")
async def addTask():
    # TODO
    NODE_STATE.queueTask()
