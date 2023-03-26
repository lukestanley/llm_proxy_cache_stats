import tiktoken

# From https://openai.com/pricing
# GPT-4 models are billed differently. The request context / text / prompt has it's token count costed seperately from the completion token cost:

"""
Ada
$0.0004 / 1K tokens
Babbage
$0.0005 / 1K tokens
Curie
$0.0020 / 1K tokens
Davinci
$0.0200 / 1K tokens
gpt-3.5-turbo,$0.002 / 1K tokens

GPT-4 models:
Model,Prompt,Completion
8K context,$0.03 / 1K tokens,$0.06 / 1K tokens
32K context,$0.06 / 1K tokens,$0.12 / 1K tokens
"""

def estimate_cost(request_text = "Hello world!", response_text = "This is a common greeting used in examples and tests.", model = "gpt-3.5-turbo"):
    def get_gpt4_model_key(request_text_length, response_text_length):
        if request_text_length <= 8000 and response_text_length <= 8000:
            return "gpt-4-8K"
        else:
            return "gpt-4-32K"

    usd_costs = {
        "gpt-3.5-turbo-input": 0.002 / 1000,
        "gpt-3.5-turbo-output": 0.002 / 1000,
        "gpt-4-8K-input": 0.03 / 1000,
        "gpt-4-32K-input": 0.06 / 1000,
        "gpt-4-8K-output": 0.06 / 1000,
        "gpt-4-32K-output": 0.12 / 1000,
        "text-davinci-003-input": 0.02 / 1000,
        "text-davinci-003-output": 0.02 / 1000,
    }

    INPUT = '-input'
    OUTPUT = '-output'

    enc = tiktoken.encoding_for_model(model)
    encoded_request_text_length = len(enc.encode(request_text))
    encoded_response_text_length = len(enc.encode(response_text))

    if "gpt-4" in model:
        model_key = get_gpt4_model_key(encoded_request_text_length, encoded_response_text_length)
        model_input_key = model_key + INPUT
        model_output_key = model_key + OUTPUT
    else:
        model_input_key = model + INPUT
        model_output_key = model + OUTPUT

    # Calculate the cost of the request based on the number of tokens and the cost per token in the dict
    request_text_cost = encoded_request_text_length * usd_costs[model_input_key]
    #print(f"Cost of request: ${request_text_cost:.6f}")

    response_text_cost = encoded_response_text_length * usd_costs[model_output_key]
    #print(f"Cost of response: ${response_text_cost:.6f}")

    total_text_cost = request_text_cost + response_text_cost
    #print(f"Total cost: ${total_text_cost:.6f}")
    return total_text_cost
