from fastapi import FastAPI
from contextlib import asynccontextmanager

from tubular_controller.controller import ControllerState, PipelineReq

CTRL_STATE = ControllerState()


@asynccontextmanager
async def lifespan(add: FastAPI):
    # TODO load configs
    CTRL_STATE.start()
    yield
    CTRL_STATE.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/pipelines")
async def getPipelines():
    pass


@app.post("/pipelines")
async def queuePipeline(pipelineReq: PipelineReq):
    CTRL_STATE.queuePipeline(pipelineReq)
