from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
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
async def getPipelines(branch: str | None = None):
    try:
        return CTRL_STATE.getPipelines(branch)
    except Exception as err:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@app.post("/pipelines", status_code=status.HTTP_201_CREATED)
async def queuePipeline(pipelineReq: PipelineReq):
    try:
        CTRL_STATE.queuePipeline(pipelineReq)
    except Exception as err:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@app.get("/node_status")
async def getNodeStatus() -> dict[str, str]:
    return CTRL_STATE.getNodeStatus()
