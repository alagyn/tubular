from fastapi import FastAPI, Response, status, routing
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import traceback
import os

from tubular_controller.controller import ControllerState, PipelineReq

CTRL_STATE = ControllerState()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@apiRouter.get("/archive_list")
async def getArchiveList(pipeline: str, branch: str, run: int) -> dict:
    return CTRL_STATE.getArchiveList(pipeline, branch, run)


@apiRouter.get("/archive")
async def getArchiveFile(pipeline: str, branch: str, run: int, file: str):
    path = CTRL_STATE.getArchiveFile(pipeline, branch, run, file)
    return FileResponse(path)


@apiRouter.get("/output_list")
async def getOutputList(pipeline: str, branch: str, run: int) -> dict:
    return CTRL_STATE.getOutputList(pipeline, branch, run)


@apiRouter.get("/output")
async def getOutputFile(pipeline: str, branch: str, run: int, file: str):
    path = CTRL_STATE.getOutputFile(pipeline, branch, run, file)
    return FileResponse(path)


@apiRouter.get("/run")
async def getRunStatuses(pipeline: str, run: int):
    return Response(content=CTRL_STATE.getRunMeta(pipeline, run),
                    media_type="application/json")


# mount these last
app.include_router(apiRouter)

FILE_DIR = os.path.abspath(os.path.dirname(__file__))
PACKAGE_ROOT = os.path.split(FILE_DIR)[0]
FRONTEND_DIR = os.path.join(PACKAGE_ROOT, "tubular-frontend", "dist")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True))
