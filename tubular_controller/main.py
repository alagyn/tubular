from fastapi import FastAPI
from contextlib import asynccontextmanager

from tubular_controller.controller import ControllerState

CTRL_STATE = ControllerState()


@asynccontextmanager
async def lifespan(add: FastAPI):
    # TODO load configs
    CTRL_STATE.start()
    yield
    CTRL_STATE.stop()


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/pipelines")
async def getPipelines():
    pass
