from typing import Dict, Any

from tubular_node.node import NodeState, TaskRequest

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
        "task_status": NODE_STATE.taskStatus.name,
    }


@app.post("/queue")
async def addTask(task: TaskRequest):
    NODE_STATE.queueTask(task)
