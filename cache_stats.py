import json
import re
from pathlib import Path

import msgpack
import pandas as pd
import streamlit as st


cache_file = "openai_cache.msgpack"
cache = {}

if Path(cache_file).is_file():
    with open(cache_file, "rb") as f:
        cache = msgpack.unpackb(f.read(), raw=False)

df = pd.DataFrame(cache.values())

def decode_streamed_http_response(response_data):
    combined_string = ""
    chunks = response_data.split("data: ")

    for chunk in chunks:
        if chunk.strip() == "[DONE]":
            break
        if not chunk:
            continue


        json_data = json.loads(chunk)
        content=''
        try:
            content = json_data['choices'][0]['text']
        except:
            content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
        combined_string += content
    return combined_string

def decode_input_messages(request_data):
    request_data = json.loads(request_data)
    return request_data["messages"]

def display_json_as_table(data):
    if not data:
        return ""
    
    table_text = "Role\tContent\n\n"
    
    for item in data:
        content = item.get("content")
        role = item.get("role")
        table_text += f"{role}\t{content}\n\n"
    
    return table_text


def app():
    st.title("OpenAI API Analytics")

    # Create a new DataFrame with the desired columns
    data = []
    for _, row in df.iterrows():
        request_data = json.loads(row["request_data"].decode())
        messages = request_data.get('messages', None)
        if messages:
            messages = display_json_as_table(messages)
        prompt = request_data.get('prompt',None)
        response_content = row["content"].decode()
        data.append({
            "url": row["url"],
            #"messages": display_json_as_table(messages),
            "input": messages or prompt[0],
            "content": decode_streamed_http_response(response_content),
            #"raw_content": response_content,
            "response_length": len(decode_streamed_http_response(response_content))
        })
    df_new = pd.DataFrame(data)
    table = df_new[["url", "input", "content","response_length"]]
    # Display the table
    st.table(table)


if __name__ == "__main__":
    app()
