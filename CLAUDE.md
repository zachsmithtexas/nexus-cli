# Prompt for Claude Code — Integrate Providers, Gemini Key Rotation, Per‑Model Limits, Open PR

> Paste this into **Claude Code** (or Codex). Acts as a senior platform engineer to merge new env + models, wire providers (Groq/Together/OpenRouter/GAIS), add **Gemini multi‑key rotation**, enforce **per‑model rate limits**, and open a PR.

---

## Repo context

- I placed **`.env.new`**, **`models.yaml.new`**, and **`READ_ME_KEY_ROTATION.md`** in the repo root (WSL).
- Existing config is under `config/` (e.g., `config/models.yaml`, `config/roles.yaml`, `config/settings.toml`).
- Python 3.11 project, Makefile targets: `setup`, `run`, `bot`, `watch`, `lint`, `test`.
- Providers to support: **groq**, **together**, **openrouter**, **google_ai_studio (Gemini 2.x/2.5 only)**, plus our local CLIs (`codex_cli`, `claude_code`).

---

## Tasks (do these in order)

### 1) Create a working branch
- Name: `feat/providers-groq-together-gemini-rotation`
- Start a running worklog in `docs/DEVLOG.md` and append as you go.

### 2) Merge environment variables
1. If `.env` exists, back it up to `.env.bak.<timestamp>`.
2. Merge **.env** from `.env.new` **without overwriting existing values**.
3. Ensure these keys exist (empty if unknown):
   - `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`, `DEEPSEEK_API_KEY`
   - `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, `GOOGLE_API_KEY_3`, `GOOGLE_API_KEY_4`, `GOOGLE_API_KEY_5`
   - `DISCORD_BOT_TOKEN`, `USE_PAID_MODELS`
4. Remove `.env.new` after merge.

### 3) Replace/merge `config/models.yaml`
1. Back up `config/models.yaml` to `config/models.yaml.bak.<timestamp>` if present.
2. Replace with **`models.yaml.new`**, but **preserve any existing `provider_route` slugs** that aren’t in the new file by merging them.
3. Ensure `providers:` explicitly contains:
   ```yaml
   groq:
     kind: http
     base_url: https://api.groq.com/openai/v1
     env_key: GROQ_API_KEY
   together:
     kind: http
     base_url: https://api.together.ai/v1
     env_key: TOGETHER_API_KEY
   openrouter:
     kind: http
     base_url: https://openrouter.ai/api/v1
     env_key: OPENROUTER_API_KEY
   google_ai_studio:
     kind: http
     base_url: https://generativelanguage.googleapis.com
     api_keys: [${GOOGLE_API_KEY_1}, ${GOOGLE_API_KEY_2}, ${GOOGLE_API_KEY_3}, ${GOOGLE_API_KEY_4}, ${GOOGLE_API_KEY_5}]
     rotation: { strategy: round_robin, cooldown_seconds: 60 }
   codex_cli:
     kind: cli
     cmd: ["codex", "chat", "--model", "${MODEL}", "--stdin"]
   claude_code:
     kind: cli
     cmd: ["claude", "--model", "${MODEL}"]
   ```
4. Remove `models.yaml.new` when done.

### 4) Provider adapters (HTTP & CLI)
- Folder: `connectors/providers/` with a common base:
  ```python
  class Provider(BaseProvider):
      name = "groq"  # etc
      def complete(self, prompt: str, **kwargs) -> str: ...
  ```
- **groq.py / together.py / openrouter.py**: OpenAI‑compatible JSON POST to each `base_url`, header `Authorization: Bearer <key>`.
- **google_ai_studio.py** (update/new) must:
  - Read `api_keys` array + `rotation` config from `models.yaml`.
  - Keep current key index in `.cache/google_ai_studio.keyidx` (create folder if missing).
  - On **HTTP 429/quota**, advance to next key (round‑robin), persist index, sleep `cooldown_seconds`, and retry.
  - Respect `USE_PAID_MODELS=false` by skipping any paid‑only routes we may mark later.
  - Log which key index is in use.
- **codex_cli.py / claude_code.py**: Spawn the CLI process (stdin/stdout), pass `--model ${MODEL}` as needed.

### 5) Per‑model rate limiting
1. If not present, create `config/limits.yaml` with shape:
   ```yaml
   providers:
     groq:
       models:
         llama-3.1-8b-instant: { rpm: 30, tpm: 7000 }
         # add others from our CSV if available
   ```
2. Add a small limiter in the router:
   - Before each request, check model’s `rpm/tpm`.
   - If exceeding, either **sleep** until safe or **fall back** to the next chain item.
   - Window granularity: 60s for RPM; keep a rolling token count for TPM.
   - In‑memory state is OK for now.

### 6) Router behavior
- Read `config/roles.yaml` & `config/models.yaml`.
- If `USE_PAID_MODELS=false`, **skip paid models** when traversing a chain.
- On provider/network error (non‑429): try next fallback.
- On 429: obey per‑model limits or **rotate GAIS key**.
- Print a concise routing trace: provider → model → latency.

### 7) Documentation
- Move the provided `READ_ME_KEY_ROTATION.md` into `config/` and reference it from `README.md`.
- Update `README.md`:
  - List all env vars (including 5× Google keys).
  - “How key rotation works” (summary) and “Per‑model rate limits” sections.
- Append a short section to `docs/DEVLOG.md` summarizing what changed.

### 8) Minimal tests
- `tests/test_rotation_google.py`: mock HTTP 429 from GAIS; assert key index increments & wraps.
- `tests/test_rate_limit.py`: tiny rpm=1 config; two sequential calls → second should sleep/fallback.
- `tests/test_router_paid_flag.py`: with `USE_PAID_MODELS=false`, ensure paid entries are skipped.

### 9) QA run
- `make setup && make lint && make test`
- Smoke:
  - Only `GOOGLE_API_KEY_1` set (others blank) → adapter handles blanks gracefully.
  - One dry‑run call each to Groq/Together/OpenRouter (verify headers/URL formed).

### 10) Commit & PR
- Commits:
  - `chore(env): merge .env.new and add key scaffolding`
  - `feat(config): merge models.yaml.new + add GAIS rotation`
  - `feat(router): per-model rate limiting + paid gating`
  - `test: rotation, rate-limit, paid gating`
  - `docs: rotation guide + README`
- Open PR: `feat/providers-groq-together-gemini-rotation` → target `main`.
- PR body:
  ```md
  ### Summary
  Adds Groq/Together providers, Gemini (GAIS) multi-key rotation, and per-model limits.

  ### Changes
  - Merged .env.new → .env; added GOOGLE_API_KEY_1..5
  - Replaced config/models.yaml with new providers (+ preserved prior routes)
  - Implemented google_ai_studio adapter with round-robin rotation & cooldown
  - Enforced per-model rpm/tpm from config/limits.yaml
  - Tests & docs

  ### How to test
  - Set dummy GOOGLE_API_KEY_1
  - make setup && make test
  - make run (observe routing + rotation logs)

  ### Rollback
  - Restore config/models.yaml.bak.<ts> and .env.bak.<ts>
  ```

---

## Acceptance criteria (all must pass)
- `.env` contains **all** new keys; existing values preserved.
- `config/models.yaml` lists **groq**, **together**, **openrouter**, **google_ai_studio** with an **api_keys** array.
- GAIS adapter rotates keys on 429 & persists index to `.cache/google_ai_studio.keyidx`.
- Router enforces per‑model rpm/tpm; falls back or sleeps safely.
- `USE_PAID_MODELS=false` skips paid models in chains.
- `make lint && make test` succeed.
- README updated; rotation guide present.
- PR opened with the template above and CI green (if applicable).

**When finished:** post the PR URL and paste a short routing/rotation log snippet from a local smoke test.
