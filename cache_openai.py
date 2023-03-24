import json
import threading
from time import sleep
from pathlib import Path
from hashlib import sha1

import httpx
import msgpack
from quart import Quart, Response, request

app = Quart(__name__)

cache_file = "openai_cache.msgpack"
cache = {}

if Path(cache_file).is_file():
    with open(cache_file, "rb") as f:
        cache = msgpack.unpackb(f.read(), raw=False)


def save_cache_periodically():
    previous_cache = None
    while True:
        if cache != previous_cache:
            with open(cache_file, "wb") as f:
                f.write(msgpack.packb(cache, use_bin_type=True))
            previous_cache = cache.copy()
        sleep(5)

def generate_cache_key(url, method, headers, data):
    headers_str = str(dict(url=url, method=method, headers=headers, data=data))
    headers_hash = sha1(headers_str.encode()).hexdigest()
    return f"{url}_{headers_hash}"

async def forward_request(url, method, headers, data):
    async with httpx.AsyncClient() as client:
        print(method)
        print(url)
        async with client.stream(method, url, headers=headers, data=data) as response:
            content = await response.aread()
            return response, content


@app.route(
    "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
)
async def proxy(path):
    # Get the request data, method, and headers
    data = await request.get_data()
    method = request.method
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }

    # Set the target URL for the OpenAI API
    target_url = f"https://api.openai.com/{path}"

    cache_key = generate_cache_key(target_url, method, headers, data)

    # Check if the response is cached
    cached_response = cache.get(cache_key)
    if cached_response:
        print("Using cache for:", cache_key)
        return Response(cached_response["content"], content_type=cached_response["content_type"])

    # Forward the request to the OpenAI API
    response, content = await forward_request(target_url, method, headers, data)

    # Stream the response
    async def stream_response():
        async for chunk in response.aiter_bytes():
            yield chunk
    
    content_type = response.headers.get("Content-Type", "application/json")
    streamed_response = Response(stream_response(), content_type=content_type)

    # Cache the response after the request has finished
    # Only cache successful responses with a status code of 200 OK or 203 Non-Authoritative Information
    if response.status_code in [200, 203]:
        # Cache the response after the request has finished
        cache[cache_key] = {
            "url": target_url,
            "headers": headers,
            "content": content,
            "request_data": data,
            "content_type": content_type,
            "status_code": response.status_code
        }

    return streamed_response


if __name__ == "__main__":
    threading.Thread(target=save_cache_periodically, daemon=True).start()
    app.run(debug=True, port=5000)
