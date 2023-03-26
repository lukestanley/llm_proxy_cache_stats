import json
from costing import estimate_cost

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
                json_data.get("choices", [{}])[0].get(
                    "delta", {}).get("content", "")
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

def stats_template(cache={}, OPENAI_API_BASE="https://api.openai.com/v1"):
    data = []
    total_request_costings_estimate = 0
    for _, row in cache.items():
        request_data = json.loads(row["request_data"].decode())
        messages = request_data.get("messages", None)
        if messages:
            messages = format_chat_input(messages)
        prompt = request_data.get("prompt", None)
        response_content = row["content"].decode()
        input_data = messages or prompt[0]
        response_text = decode_streamed_http_response(response_content)
        model = request_data.get("model", None)
        estimated_request_cost = estimate_cost(request_text = input_data, response_text = response_text, model = model)
        total_request_costings_estimate += estimated_request_cost
        data.append(
            {
                "url": row["url"].replace(OPENAI_API_BASE, ""),
                "input": input_data,
                "content": decode_streamed_http_response(response_content),
                "response_length": len(response_text),
                "model": model,
                "cost_estimate": f"${estimated_request_cost:.6f}",
                "request_method": row.get("method", "?")
            }
        )

    table_rows = ""
    for row in data:
        table_rows += f"""
        <tr>
            <td>{row['url']}</td>
            <td>{row['input']}</td>
            <td>{row['content']}</td>
            <td>{row['response_length']}</td>
            <td>{row['model']}</td>
            <td>{row['cost_estimate']}</td>
            <td>{row['request_method']}</td>
        </tr>
        """
    total_request_costings_estimate_formatted = f"${total_request_costings_estimate:.6f}"

    html = f"""
    <html>
        <head>
            <title>Cached LLM Responses</title>
        </head>
        <body>
            <h1>Cached Responses</h1>
            <h3>Total Cost Estimate: {total_request_costings_estimate_formatted}</h3>
            <table>
                <tr>
                    <th>URL</th>
                    <th>Input</th>
                    <th>Response</th>
                    <th>Length</th>
                    <th>Model</th>
                    <th>Cost est.</th>
                    <th>Method</th>
                </tr>
                {table_rows}
            </table>
        </body>
    </html>
    """
    
    return html
