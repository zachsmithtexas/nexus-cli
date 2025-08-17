# Google AI Studio key rotation (Gemini 2.x/2.5)

- Provider `google_ai_studio` in `models.yaml` lists `api_keys: [${GOOGLE_API_KEY_1} ... ${GOOGLE_API_KEY_5}]`
- Your adapter should:
  1) Try key[i] for a request.
  2) On 429/quota, advance i = (i+1) % len(keys).
  3) Persist the index at `.cache/google_ai_studio.keyidx` so restarts continue.
  4) Optional: respect `rotation.cooldown_seconds` before reusing a key.

Example pseudo-code:

```python
class GoogleAISAdapter:
    def __init__(self, api_keys, cooldown):
        self.keys = api_keys
        self.idx = load_idx()  # read from .cache
        self.cooldown = cooldown
    def request(self, payload):
        for _ in range(len(self.keys)):
            key = self.keys[self.idx]
            resp = call_google(payload, key)
            if resp.status != 429:
                return resp
            self.idx = (self.idx + 1) % len(self.keys)
            save_idx(self.idx)
            time.sleep(self.cooldown)
        raise RuntimeError("All Google keys exhausted")
```

