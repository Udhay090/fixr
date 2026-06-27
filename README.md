# fixr ⚡

AI-powered CLI that explains errors and suggests fixes — using a hashtable cache + LLM combo.

## Install

```bash
pip install fixr
# or
uv add fixr
```

## Usage

```bash
# Direct
fixr "TypeError: unsupported operand type(s) for +: 'int' and 'str'"

# Pipe any command output
python script.py 2>&1 | fixr
cargo build 2>&1 | fixr
node app.js 2>&1 | fixr
g++ main.cpp 2>&1 | fixr
```

## Setup

```bash
# Set API key
fixr config --provider groq --api-key gsk_...

# Set default provider
fixr config --provider gemini

# OAuth login (Google/Gemini)
fixr login google

# Show current config
fixr config --show

# List all providers
fixr providers
```

## Free tier providers (no credit card)

| Provider | Models |
|---|---|
| groq | llama-3.3-70b-versatile |
| gemini | gemini-2.0-flash |
| mistral | mistral-small |
| openrouter | 20+ free models |
| nvidia | 100+ open models |
| cerebras | llama3.3-70b |

## How it works

```
error input
    │
    ▼
normalize + hash (sha256[:16])
    │
    ▼
cache hit? ──yes──→ instant response ⚡
    │
   no
    ▼
LLM call (provider of choice)
    │
    ▼
store in ~/.fixr/cache.json
    │
    ▼
display fix
```

Cache lives at `~/.fixr/cache.json`. Gets smarter over time.
