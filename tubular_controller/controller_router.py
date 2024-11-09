from fastapi import FastAPI, Response, status, routing
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import traceback

from tubular_controller.controller import ControllerState, PipelineReq

CTRL_STATE = ControllerState()


@asynccontextmanager
async def lifespan(add: FastAPI):
    # TODO load configs
    CTRL_STATE.start()
    yield
    CTRL_STATE.stop()


app = FastAPI(lifespan=lifespan)

apiRouter = routing.APIRouter(prefix="/api")


@apiRouter.get("/pipelines")
async def getPipelines(branch: str | None = None):
    # TODO cache results
    try:
        return CTRL_STATE.getPipelines(branch)
    except Exception as err:
        traceback.print_exception(err, chain=True)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@apiRouter.post("/pipelines", status_code=status.HTTP_201_CREATED)
async def queuePipeline(pipelineReq: PipelineReq):
    try:
        CTRL_STATE.queuePipeline(pipelineReq)
    except Exception as err:
        traceback.print_exception(err, chain=True)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@apiRouter.get("/pipeline")
async def getPipelineArgs(pipelinePath: str, branch: str | None):
    try:
        return CTRL_STATE.getPipelineArgs(pipelinePath, branch)
    except Exception as err:
        traceback.print_exception(err, chain=True)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@apiRouter.get("/runs")
async def getRuns(pipelinePath: str):
    try:
        return CTRL_STATE.getRuns(pipelinePath)
    except Exception as err:
        traceback.print_exception(err, chain=True)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(err)})


@apiRouter.get("/runs_stats")
async def getRunsStats():
    return CTRL_STATE.getRunsStats()


@apiRouter.get("/node_status")
async def getNodeStatus() -> dict[str, str]:
    return CTRL_STATE.getNodeStatus()


@apiRouter.get("/branches")
async def getBranches() -> list[str]:
    return CTRL_STATE.getBranches()


# mount these last
app.include_router(apiRouter)
app.mount("/", StaticFiles(directory="tubular-frontend/dist", html=True))
