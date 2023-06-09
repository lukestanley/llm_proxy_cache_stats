import uvicorn
import threading
from hashlib import sha1
from pathlib import Path
from time import sleep

import httpx
import msgpack
from starlette.applications import Starlette
from starlette.responses import Response, StreamingResponse

from ui_utils import  stats_template

app = Starlette(debug=True)

OPENAI_API_BASE = "https://api.openai.com/"

CACHE_FILENAME = "openai_cache.msgpack"
cache = {}

if Path(CACHE_FILENAME).is_file():
    with open(CACHE_FILENAME, "rb") as f:
        cache = msgpack.unpackb(f.read(), raw=False)


def save_cache_periodically():
    """Save the cache to disk every 5 seconds if updated."""
    previous_cache = None
    while True:
        if cache != previous_cache:
            with open(CACHE_FILENAME, "wb") as f:
                f.write(msgpack.packb(cache, use_bin_type=True))
            previous_cache = cache.copy()
        sleep(5)


def generate_cache_key(url, method, headers, data):
    """Generate a unique key for the request by hashing the input parameters."""
    headers_str = str(dict(url=url, method=method, headers=headers, data=data))
    headers_hash = sha1(headers_str.encode()).hexdigest()
    return f"{url}_{headers_hash}"


async def forward_request(url, method, headers, data):
    """Forward the request to the OpenAI API"""
    async with httpx.AsyncClient() as client:
        async with client.stream(method, url, headers=headers, data=data) as response:
            content_type = response.headers.get(
                "Content-Type", response.headers.get("Media-Type", "application/json")
            )
            # we yield the type and status code
            yield content_type, response.status_code
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk  # Yield the remaining chunks of the response
            except (httpx.StreamClosed, httpx.ReadTimeout):
                pass

@app.route("/stats")
async def stats(request):
    """Display a table of cached responses with their input and output"""
    html = stats_template(cache, OPENAI_API_BASE)
    return Response(html, media_type="text/html")


@app.route("/{path:path}", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def proxy(request):
    """Proxy requests to the OpenAI API and cache the responses."""
    # Get the request data, method, and headers
    path = request.url.path[1:]
    data = await request.body()
    method = request.method
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }

    # Set the target URL for the OpenAI API
    target_url = f"{OPENAI_API_BASE}{path}"

    cache_key = generate_cache_key(target_url, method, headers, data)

    # Check if the response is cached
    cached_response = cache.get(cache_key)
    if cached_response:
        print("Using cache for:", cache_key)
        return Response(
            cached_response["content"], media_type=cached_response["content_type"]
        )

    # Forward the request to the OpenAI API
    response_chunks = forward_request(target_url, method, headers, data)
    content_type, status_code = await response_chunks.__anext__()  # Get the content type from the async generator
    print("content_type:",content_type)
    print("status_code:",status_code)
    async def stream_response(response_chunks):
        chunks = []
        async for chunk in response_chunks:
            chunks.append(chunk)
            yield chunk
        if status_code != 200:
            return
        content = b"".join(chunks)
        cache[cache_key] = {
            "url": target_url,
            "headers": headers,
            "content": content,
            "request_data": data,
            "content_type": content_type,
            "status_code": status_code,
            "method": method,
        }
    return StreamingResponse(stream_response(response_chunks), media_type=content_type)


if __name__ == "__main__":
    threading.Thread(target=save_cache_periodically, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=5000)
