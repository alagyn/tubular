from typing import Dict, Any

from tubular_node.node import NodeState, TaskRequest

from fastapi import FastAPI
from fastapi.responses import FileResponse
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
async def getStatus(updateConfig: bool = False):
    if updateConfig:
        print("Setting need update")
        NODE_STATE.needUpdateConfig = True
    return {
        "status": NODE_STATE.status.name,
        "task_status": NODE_STATE.taskStatus.name,
    }


@app.get("/archive")
async def getArchive(task: TaskRequest) -> FileResponse:
    archive = NODE_STATE.getArchiveFile(task)
    return FileResponse(archive)


@app.get("/output")
async def getOutput(task: TaskRequest) -> FileResponse:
    output = NODE_STATE.getOutputFile(task)
    return FileResponse(output)


@app.post("/queue")
async def addTask(task: TaskRequest):
    NODE_STATE.queueTask(task)
