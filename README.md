# fixr ⚡

> AI-powered CLI that explains errors and suggests fixes — using a hashtable cache + LLM hybrid.

```bash
pip install fixr-cli
```

---

## How it works

```
your error
    │
    ▼
SHA256 cache lookup ─> hit ─> instant fix ⚡ (no LLM call)
    │
   miss
    ▼
LiteLLM → Groq / Gemini / Mistral / OpenAI / Anthropic / ...
    │
    ▼
cache result → show fix
```

Identical errors are resolved instantly from cache. The tool gets faster the more you use it.

---

## Usage

```bash
# Run any file — fxr captures the error automatically
fxr script.py
fxr main.rs
fxr app.js
fxr main.cpp
fxr Main.java
fxr main.go

# Paste an error directly
fxr "TypeError: unsupported operand type(s) for +: 'int' and 'str'"

# Pipe any command
python script.py 2>&1 | fxr
cargo build 2>&1 | fxr
```

---

## Setup

```bash
# 1. Install
pip install fixr-cli
# or
uv add fixr-cli

# 2. Run setup wizard (select provider, model, paste API key)
fxr setup
```

Setup takes 30 seconds. Free API keys work — no credit card needed.

---

## Free Tier Providers

| Provider | Free API | Speed |
|---|---|---|
| [Groq](https://console.groq.com) | ✅ | ⚡⚡ Faster (free) |
| [Cerebras](https://inference.cerebras.ai) | ✅ | ⚡ Fast (free) |
| [Gemini](https://aistudio.google.com) | ✅ | ✅ Good |
| [Mistral](https://console.mistral.ai) | ✅ | ✅ Good |
| [OpenRouter](https://openrouter.ai) | ✅ | ✅ Good |
| Ollama | ✅ Local | Depends on hardware |
| OpenAI | ❌ Paid | ⚡⚡⚡ Fastest overall |
| Anthropic | ❌ Paid | ⚡ Fast |

Default: **Groq → llama-3.3-70b-versatile**

---

## Commands

```bash
fxr setup                              # interactive setup wizard
fxr providers                          # list all providers + models
fxr config --show                      # show current config
fxr config --provider groq --api-key   # set API key
fxr add-model <provider> <model>       # add custom model
fxr clear-cache                        # wipe local cache
```

---

## Languages Supported

Python · JavaScript · TypeScript · Rust · C · C++ · Java · Go · Ruby · PHP · Bash · Lua · Perl · R · Swift · Kotlin

---

## Architecture

```
fixr/
├── main.py       # Typer CLI — commands + cli() entrypoint
├── cache.py      # SHA256 hashtable — ~/.fixr/cache.json
├── llm.py        # LiteLLM routing — 10+ providers
├── config.py     # Config store — ~/.fixr/config.json
└── auth.py       # API key storage + OAuth scaffold
```

---

## Stack

Python · Typer · LiteLLM · Rich · Hatchling · uv

---

## License

MIT
