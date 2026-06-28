# BYO — Bring Your Own provider

If your LLM vendor isn't in canopy's built-in list (Anthropic, OpenAI, Gemini, Bedrock, Cohere, OpenRouter), use **BYO** to wire it in 30 lines.

## When to use BYO

- Your company has an in-house LLM gateway
- You're using a vendor we haven't shipped yet (Replicate, AI21, Writer, etc.)
- You want to wrap canopy around a local model with custom pre/post-processing
- You're prototyping a new provider before contributing it upstream

## The contract

canopy's `Provider` protocol has one method:

```python
def complete(self, system: str, user: str) -> str:
    """Return the LLM's response text given a system and user prompt."""
```

That's it. canopy calls `complete(system, user)` once per batch and parses the response as JSON `{path: description}`.

## Minimal example

```python
from canopy.providers import BYOProvider

def my_complete(system: str, user: str) -> str:
    import urllib.request, json
    req = urllib.request.Request(
        "https://api.example.com/v1/chat",
        data=json.dumps({"system": system, "user": user}).encode(),
        headers={"authorization": "Bearer MY_KEY"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["text"]

provider = BYOProvider(complete_fn=my_complete)
```

Then pass it to `canopy.fill_missing()` directly, or wire it through `setup.py` (see "Advanced: extending setup" below).

## Wrapping a different vendor body shape

Most BYO adapters are just "translate canopy's (system, user) into vendor-specific body, extract text from vendor-specific response". Example for AI21 (illustrative — adjust to their actual API):

```python
from canopy.providers import BYOProvider

def ai21_complete(system: str, user: str) -> str:
    import urllib.request, json
    req = urllib.request.Request(
        "https://api.ai21.com/studio/v1/j2-mid/complete",
        data=json.dumps({
            "prompt": f"{system}\n\n{user}",
            "maxTokens": 2048,
        }).encode(),
        headers={"authorization": "Bearer YOUR_AI21_KEY"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["completions"][0]["data"]["text"]

# Use it
provider = BYOProvider(complete_fn=ai21_complete)
```

## Exceptions

If your function raises, the exception propagates unchanged. canopy doesn't swallow errors — `canopy fill` exits with a non-zero status and prints the error to stderr.

If you want resilience (retry, fallback), wrap it yourself:

```python
import time

def resilient_complete(system: str, user: str, *, attempts: int = 3) -> str:
    for i in range(attempts):
        try:
            return my_complete(system, user)
        except Exception as e:
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)  # exponential backoff

provider = BYOProvider(complete_fn=resilient_complete)
```

## Advanced: extending setup

If you want `canopy setup --provider my-vendor` to work, add an entry to `canopy.setup.KNOWN_PROVIDERS` and a default model. Then add a branch in `canopy.fill.fill_missing()`'s provider-selection block to instantiate your class.

Or — better — open an issue or PR to add it as a first-class provider. See [CONTRIBUTING.md](../../CONTRIBUTING.md) (TODO).

## Why this exists

BYO is the seed of a future standalone "model provider component" library. If canopy grows, the `Provider` Protocol + a curated set of adapters could be extracted into a separate PyPI package, and other tools (chat UIs, eval harnesses, code analyzers) could use it independently.

For now, BYO lets you ship today without waiting for us to ship the adapter.