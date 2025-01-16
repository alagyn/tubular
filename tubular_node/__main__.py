import os

if __name__ == '__main__':
    import uvicorn

    try:
        port = int(os.environ["TUBULAR_PORT"])
    except KeyError:
        port = 8080

    uvicorn.run("tubular_node.node_router:app", port=port)
