# OpenAI Luna - SOTA model is our benchmark
uv run python classify.py --input ../data/conversations/traces.jsonl \
  --model openai:gpt-6-luna --reasoning low --output results-gpt-6-luna-low.jsonl

uv run python classify.py --input ../data/conversations/traces.jsonl \
  --model openai:gpt-6-astra --reasoning low --output results-gpt-6-astra-low.jsonl



# DeepSeek-V4.1-Flash (default model)
uv run python classify.py --input ../data/conversations/traces.jsonl \
  --model nebius:deepseek-ai/DeepSeek-V4.1-Flash --output results-deepseek-v4.1-flash.jsonl

# GLM-5.3-Flash
uv run python classify.py --input ../data/conversations/traces.jsonl \
  --model nebius:zai-org/GLM-5.3-Flash --output results-glm-5.3-flash.jsonl

# Qwen3.5-397B-A17B
uv run python classify.py --input ../data/conversations/traces.jsonl \
  --model nebius:Qwen/Qwen3.5-397B-A17B --output results-qwen3.5-397b.jsonl