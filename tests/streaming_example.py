import openai
import langchain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
openai.api_base = "http://localhost:5000/v1"

prompt = "Make up a funny 3 line poem about a pirate sock company, that starts with their name."

call_manager = langchain.callbacks.base.CallbackManager(
    [StreamingStdOutCallbackHandler()]
)
gpt3 = langchain.llms.OpenAI(
    temperature=0.9, streaming=True, 
    callback_manager=call_manager, verbose=True
)
gpt_chat = langchain.llms.OpenAIChat(
    temperature=0.9, streaming=True, 
    callback_manager=call_manager, verbose=True
)

gpt3(prompt)
print()
print("_" * 80)
gpt_chat(prompt)
