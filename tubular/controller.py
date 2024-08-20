from fastapi import FastAPI
from contextlib import asynccontextmanager


class ControllerState:

    def __init__(self) -> None:
        pass


CTRL_STATE = ControllerState()


@asynccontextmanager
async def lifespan(add: FastAPI):
    # TODO load configs

    yield


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
