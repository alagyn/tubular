import os

if __name__ == '__main__':
    import uvicorn

    try:
        port = int(os.environ["TUBULAR_PORT"])
    except KeyError:
        port = 8080

    try:
        host = os.environ["TUBULAR_HOST"]
    except KeyError:
        host = "0.0.0.0"

    uvicorn.run("tubular_controller.controller_router:app",
                port=port,
                host=host)
