import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    """
    Count tokens in the given text using the specified model's encoding.
    Adjust the model parameter if Deepseek V3 Chat uses a different one.
    """
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)