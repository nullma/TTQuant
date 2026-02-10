import asyncio
import websockets
import json
import os
import sys

# 代理配置
PROXY_URL = "http://127.0.0.1:7897"

async def test_okx_ws():
    uri = "wss://ws.okx.com:8443/ws/v5/public"
    print(f"Connecting to {uri} via proxy {PROXY_URL}...")
    
    # 构建代理连接 (注意: websockets 库本身不直接支持 HTTP 代理, 这里简化测试)
    # 我们先尝试直连测试 (如果代理是透明代理)
    # 或者我们使用 requests 测试 HTTP 连通性作为替代?
    # 更好的方式是使用 websockets_proxy 库, 但可能未安装.
    
    # 让我们改用简单的 HTTP 请求测试 WebSocket 握手端口是否通
    import requests
    try:
        proxies = {'http': PROXY_URL, 'https': PROXY_URL}
        print("Testing HTTP connectivity to OKX API...")
        resp = requests.get("https://www.okx.com/api/v5/public/time", proxies=proxies, timeout=10)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200:
            print("✅ HTTP Connectivity OK")
        else:
            print("❌ HTTP Failed")
            
    except Exception as e:
        print(f"❌ HTTP Error: {e}")

    # 尝试简单的 WebSocket 握手 (如果环境允许)
    # 由于 Python 环境限制, 我们可能无法直接测试 WebSocket + Proxy
    # 但我们可以打印出下一步建议
    
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_okx_ws())
