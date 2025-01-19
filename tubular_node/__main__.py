import os

if __name__ == '__main__':
    import uvicorn

    try:
        port = int(os.environ["TUBULAR_PORT"])
    except KeyError:
        port = 8081

    try:
        host = os.environ["TUBULAR_HOST"]
    except KeyError:
        host = "0.0.0.0"

    uvicorn.run("tubular_node.node_router:app", host=host, port=port)
