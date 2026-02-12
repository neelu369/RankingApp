import replicate
import os
import time

os.environ["REPLICATE_API_TOKEN"] = "your_replicate_api_key"

MODEL = "meta/meta-llama-3-8b-instruct"

def call_llama3_with_logging(prompt: str):
    start_time = time.time()

    # Count input tokens
    input_tokens = count_tokens(prompt)

    # Call Replicate
    output = replicate.run(
        MODEL,
        input={
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.7
        }
    )

    response_text = "".join(output)

    # Count output tokens
    output_tokens = count_tokens(response_text)

    latency = time.time() - start_time

    log_data = {
        "model": MODEL,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "latency_seconds": round(latency, 2)
    }

    print("API CALL LOG:", log_data)

    return response_text