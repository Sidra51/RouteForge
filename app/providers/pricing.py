# Pricing configurations in USD per token (derived from Price per 1,000,000 tokens)
MODEL_PRICING = {
    # --- Google Gemini Models ---
    "gemini-1.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-1.5-pro": {
        "input": 1.25 / 1_000_000,
        "output": 5.00 / 1_000_000,
    },
    "gemini-2.0-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-2.0-flash-lite": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-2.0-flash-lite-001": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-2.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-2.5-pro": {
        "input": 1.25 / 1_000_000,
        "output": 5.00 / 1_000_000,
    },

    # --- OpenAI Models ---
    "gpt-4o": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000,
    },
    "gpt-4o-mini": {
        "input": 0.150 / 1_000_000,
        "output": 0.600 / 1_000_000,
    },
    "o1-mini": {
        "input": 3.00 / 1_000_000,
        "output": 12.00 / 1_000_000,
    },

    # --- DeepSeek Models ---
    "deepseek-chat": {
        "input": 0.14 / 1_000_000,
        "output": 0.28 / 1_000_000,
    },
    "deepseek-reasoner": {
        "input": 0.55 / 1_000_000,
        "output": 2.19 / 1_000_000,
    },

    # --- Groq Models ---
    "qwen/qwen3.8-27b": {
        "input": 0.20 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "openai/gpt-oss-20b": {
        "input": 0.20 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "allam-2-7b": {
        "input": 0.10 / 1_000_000,
        "output": 0.15 / 1_000_000,
    },
    "llama-3.1-8b-instant": {
        "input": 0.05 / 1_000_000,
        "output": 0.08 / 1_000_000,
    },
    "llama-3.3-70b-versatile": {
        "input": 0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    },
    "llama-3.1-70b-versatile": {
        "input": 0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    }
}
