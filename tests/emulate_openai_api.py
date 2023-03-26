from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route
import asyncio
import uvicorn
from subprocess import check_output

app = Starlette(debug=True)
# Defining an async generator function that yields timestamps


async def stream_timestamps():
    for i in range(5):
        yield f"Timestamp {i}: {check_output('date')}\n"
        await asyncio.sleep((0.2*i)+0.2)

# Defining endpoints that return streaming responses
@app.route("/stream", methods=["GET"])
async def stream(request):
    return StreamingResponse(stream_timestamps(), media_type="text/plain")

# This one has a route that matches the OpenAI API
@app.route("/v1/completions", methods=["GET"])
async def stream(request):
    return StreamingResponse(stream_timestamps(), media_type="text/plain")

# Running the app with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
