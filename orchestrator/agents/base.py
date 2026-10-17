from openai import OpenAI
from config import CRUSOE_API_KEY, CRUSOE_BASE_URL, MODEL_NAME, MAX_TOKENS


def get_client() -> OpenAI:
    if not CRUSOE_API_KEY:
        raise ValueError(
            "CRUSOE_API_KEY not set. Export it or add it to a .env file."
        )
    return OpenAI(api_key=CRUSOE_API_KEY, base_url=CRUSOE_BASE_URL)


def call_model(system: str, user: str, temperature: float = 0.3) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content or ""
