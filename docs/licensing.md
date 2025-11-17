# Licensing and Plans

This repo includes a simple licensing layer that can gate certain agents and
features on top of the API Gateway plans. The goal is:

- Don9t break local development when env vars are missing.
- Let you *optionally* enforce hard licensing in production.
- Keep everything driven by environment variables.

## Core Env Vars

These apply globally to all licensed features:

```bash
# Key used to call the API Gateway /whoami endpoint
LICENSE_API_KEY=md_your_license_key

# Where to find the gateway
LICENSE_GATEWAY_URL=http://127.0.0.1:8010  # or your deployed URL

# If set to 1/true/yes, failed license checks EXIT the process
REQUIRE_LICENSE=0
```

Behavior:

- If `LICENSE_API_KEY` is **missing**, agents log a warning and continue in
  dev mode (no hard gating).
- If `LICENSE_API_KEY` is set, each agent calls `GET {LICENSE_GATEWAY_URL}/whoami`
  with `X-API-Key: LICENSE_API_KEY` and reads the returned `plan`.
- If `REQUIRE_LICENSE` is truthy, any failure (bad key, network error, plan too
  low) causes a clean `SystemExit(1)`.

## Per-Feature Minimum Plans

Each feature can require a minimum plan. Plans are ranked in
`src/licensing.py` as:

```text
free < pro < team < enterprise
```

Per-feature env vars:

```bash
LICENSE_MIN_PLAN_FOCUS=free    # Focus Agent
LICENSE_MIN_PLAN_PHONE=free    # Phone/Twilio Agent
LICENSE_MIN_PLAN_VIDEO=free    # Video (Sora) Agent
LICENSE_MIN_PLAN_CLIPS=free    # Realtime Clips Agent
```

You can raise these per deployment. For example, to require **pro** for
phone and video and **team** for clips:

```bash
LICENSE_MIN_PLAN_FOCUS=free
LICENSE_MIN_PLAN_PHONE=pro
LICENSE_MIN_PLAN_VIDEO=pro
LICENSE_MIN_PLAN_CLIPS=team
```

## How Agents Use Licensing

All checks are done through `ensure_feature_license(feature: str)` in
`src/licensing.py`. Agents call it once on startup:

- **Focus Agent** (`src/agents/focus_agent.py`)
  ```python
  ensure_feature_license("focus")
  ```

- **Phone Agent** (`src/agents/phone_agent.py`)
  ```python
  if not TESTING_MODE:
      load_dotenv()
      ensure_feature_license("phone")
  ```
  In `TESTING_MODE = True`, no license check is performed so local terminal
  testing never breaks.

- **Video Agent** (`src/agents/video_agent.py`)
  ```python
  load_dotenv()
  ensure_feature_license("video")
  ```

- **Realtime Clips Agent** (`src/agents/realtime_clips_agent.py`)
  ```python
  ensure_feature_license("clips")
  ```

## Gateway Contract

The licensing helper expects the gateway to expose a simple `/whoami`
endpoint that returns JSON like:

```json
{
  "plan": "pro",
  "key_hash": "...",
  "limits": { "rpm": 600 }
}
```

Only the `plan` field is required. Everything else is ignored by the
licensing layer and can evolve independently.

## Recommended Patterns

- In dev, set **no** license env vars to keep everything frictionless.
- In staging/production, set:
  - `LICENSE_API_KEY` to a key managed in the keystore.
  - `LICENSE_GATEWAY_URL` to your deployed gateway.
  - `REQUIRE_LICENSE=1` only when youre ready to enforce hard gating.
  - Per-feature `LICENSE_MIN_PLAN_*` envs to align with your pricing.

This keeps licensing logic centralized, simple, and easy to tune as you
iterate on plans and product tiers.
