import json
import threading
from hashlib import sha1
from pathlib import Path
from time import sleep

import httpx
import msgpack
from quart import Quart, Response, request, render_template_string

app = Quart(__name__)

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
        print(method)
        print(url)
        async with client.stream(method, url, headers=headers, data=data) as response:
            content = await response.aread()
            return response, content


@app.route(
    "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
)
async def proxy(path):
    """Proxy requests to the OpenAI API and cache the responses."""
    # Get the request data, method, and headers
    data = await request.get_data()
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
            cached_response["content"], content_type=cached_response["content_type"]
        )

    # Forward the request to the OpenAI API
    response, content = await forward_request(target_url, method, headers, data)

    # Stream the response
    async def stream_response():
        async for chunk in response.aiter_bytes():
            yield chunk

    content_type = response.headers.get("Content-Type", "application/json")
    streamed_response = Response(stream_response(), content_type=content_type)

    # Cache successful responses with a status code of 200 OK or 203 Non-Authoritative Information
    # TODO: Further restrict caches by URL allow or ignore lists
    if response.status_code in [200, 203]:
        # Cache the response after the request has finished
        cache[cache_key] = {
            "url": target_url,
            "headers": headers,
            "content": content,
            "request_data": data,
            "content_type": content_type,
            "status_code": response.status_code,
        }

    return streamed_response


def decode_streamed_http_response(response_data):
    """Decode the streamed HTTP response of text or chat response streams"""

    combined_string = ""
    chunks = response_data.split("data: ")

    for chunk in chunks:
        if chunk.strip() == "[DONE]":
            break
        if not chunk:
            continue

        json_data = json.loads(chunk)
        content = ""
        # Try to extract chunks of text, but fall back to chat:
        try:
            content = json_data["choices"][0]["text"]
        except Exception:
            content = (
                json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
            )
        combined_string += content
    return combined_string


def decode_input_messages(request_data):
    """Decode the input messages from the request data"""
    request_data = json.loads(request_data)
    return request_data["messages"]


def format_chat_input(data):
    """Format the messages input for the stats page"""
    if not data:
        return ""

    table_text = "Role\tContent\n\n"

    for item in data:
        content = item.get("content")
        role = item.get("role")
        table_text += f"{role}\t{content}\n\n"

    return table_text


@app.route("/stats")
async def stats():
    """Display a table of cached responses with their input and output"""
    data = []
    for _, row in cache.items():
        request_data = json.loads(row["request_data"].decode())
        messages = request_data.get("messages", None)
        if messages:
            messages = format_chat_input(messages)
        prompt = request_data.get("prompt", None)
        response_content = row["content"].decode()
        data.append(
            {
                "url": row["url"],
                "input": messages or prompt[0],
                "content": decode_streamed_http_response(response_content),
                "response_length": len(decode_streamed_http_response(response_content)),
            }
        )

    table_template = """
    <table>
        <tr>
            <th>URL</th>
            <th>Input</th>
            <th>Content</th>
            <th>Response Length</th>
        </tr>
        {% for row in data %}
        <tr>
            <td>{{ row.url }}</td>
            <td>{{ row.input }}</td>
            <td>{{ row.content }}</td>
            <td>{{ row.response_length }}</td>
        </tr>
        {% endfor %}
    </table>
    """
    return await render_template_string(table_template, data=data)


if __name__ == "__main__":
    threading.Thread(target=save_cache_periodically, daemon=True).start()
    app.run(debug=True, port=5000)
