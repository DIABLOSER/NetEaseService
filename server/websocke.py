from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import asyncio
import logging

app = FastAPI()

# 存储安卓ID与WebSocket连接的映射
connected_clients = {}

# 存储待处理的请求：request_id到(asyncio.Event, 结果)的映射
pending_requests = {}

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/{android_id}")
async def websocket_endpoint(websocket: WebSocket, android_id: str):
    await websocket.accept()
    connected_clients[android_id] = websocket
    logging.info(f"Android client {android_id} connected.")
    try:
        while True:
            data = await websocket.receive_text()
            # 处理来自安卓端的响应，格式为 "request_id:content"
            if ':' in data:
                request_id, content = data.split(':', 1)
                if request_id in pending_requests:
                    event, _ = pending_requests[request_id]
                    pending_requests[request_id] = (event, content)
                    event.set()  # 触发事件，通知HTTP请求处理完成
    except WebSocketDisconnect:
        logging.warning(f"Android client {android_id} disconnected.")
        if android_id in connected_clients:
            del connected_clients[android_id]
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        if android_id in connected_clients:
            del connected_clients[android_id]

@app.get("/get_input/{android_id}")
async def get_input(android_id: str):
    if android_id not in connected_clients:
        return JSONResponse(status_code=404, content={"error": "Client not connected"})
    
    websocket = connected_clients[android_id]
    request_id = str(uuid.uuid4())
    event = asyncio.Event()
    pending_requests[request_id] = (event, None)
    
    try:
        # 发送请求给安卓端，格式为 "request_id:get_input"
        await websocket.send_text(f"{request_id}:get_input")
        # 等待响应，设置超时时间（例如5秒）
        await asyncio.wait_for(event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        logging.error(f"Timeout waiting for response from {android_id}")
        del pending_requests[request_id]
        return JSONResponse(status_code=504, content={"error": "Request timeout"})
    except Exception as e:
        logging.error(f"Error sending request: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
    
    # 获取结果并清理pending_requests
    _, result = pending_requests.pop(request_id)
    return {"android_id": android_id, "input_content": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)