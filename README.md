# Nexus CLI

A powerful AI model routing and management CLI with support for multiple providers, intelligent fallbacks, and advanced features like key rotation and rate limiting.

> **New in this release:** Added Groq, Together, and Google AI Studio providers with multi-key rotation, plus comprehensive rate limiting system.

## Features

- **Multi-Provider Support**: Groq, Together, OpenRouter, Google AI Studio, Claude Code, Codex CLI, DeepSeek, and Qwen
- **Intelligent Routing**: Automatic failover between providers with rate limiting and paid model gating
- **Key Rotation**: Advanced multi-key rotation for Google AI Studio with automatic fallback on rate limits
- **Per-Model Rate Limiting**: Configurable RPM/TPM limits to stay within API quotas
- **Cost Management**: Paid model gating with `USE_PAID_MODELS` environment variable
- **Discord Integration**: Bot interface for team collaboration
- **Obsidian Integration**: Connect with your knowledge vault

## Quick Start

```bash
# Install dependencies
make setup

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the CLI
make run

# Start Discord bot
make bot
```

## Environment Variables

### Core Settings
- `USE_PAID_MODELS` - Enable/disable paid models (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)

### Provider API Keys
- `OPENROUTER_API_KEY` - OpenRouter API key
- `GROQ_API_KEY` - Groq API key  
- `TOGETHER_API_KEY` - Together API key
- `DEEPSEEK_API_KEY` - DeepSeek API key

### Google AI Studio Keys (Multi-Key Rotation)
- `GOOGLE_API_KEY_1` - Primary Google AI Studio key
- `GOOGLE_API_KEY_2` - Secondary Google AI Studio key
- `GOOGLE_API_KEY_3` - Tertiary Google AI Studio key
- `GOOGLE_API_KEY_4` - Quaternary Google AI Studio key
- `GOOGLE_API_KEY_5` - Quinary Google AI Studio key

### Discord Bot Configuration
- `DISCORD_BOT_TOKEN` - Discord bot token
- `DISCORD_APP_ID` - Discord application ID
- `DISCORD_GUILD_ID` - Discord server ID
- `DISCORD_COMMANDS_CHANNEL_ID` - Commands channel ID
- `DISCORD_UPDATES_CHANNEL_ID` - Updates channel ID

### Optional Discord Webhooks
- `COMMUNICATIONS_WEBHOOK_URL` - Communications team webhook
- `PM_WEBHOOK_URL` - Product management webhook
- `SD_WEBHOOK_URL` - Software development webhook
- `JD_WEBHOOK_URL` - John Doe webhook
- `RQE_WEBHOOK_URL` - Requirements engineering webhook

### Obsidian Integration
- `OBSIDIAN_VAULT_PATH` - Path to your Obsidian vault

## Configuration

### Models and Providers

The system supports two configuration approaches:

1. **Legacy Models** (`config/models.yaml` - models section): Simple provider-to-model mapping
2. **Provider Routes** (`config/models.yaml` - provider_routes section): Advanced routing with capabilities

#### Provider Configuration

```yaml
providers:
  groq:
    kind: http
    base_url: https://api.groq.com/openai/v1
    env_key: GROQ_API_KEY
  google_ai_studio:
    kind: http
    base_url: https://generativelanguage.googleapis.com
    api_keys: [${GOOGLE_API_KEY_1}, ${GOOGLE_API_KEY_2}, ${GOOGLE_API_KEY_3}, ${GOOGLE_API_KEY_4}, ${GOOGLE_API_KEY_5}]
    rotation: { strategy: round_robin, cooldown_seconds: 60 }
```

### Rate Limiting

Configure per-model rate limits in `config/limits.yaml`:

```yaml
providers:
  groq:
    models:
      llama-3.1-8b-instant: { rpm: 30, tpm: 7000 }
  google_ai_studio:
    models:
      gemini-2.5-pro: { rpm: 150, tpm: 10000 }
```

### Role-Based Routing

Define AI roles and their provider chains in `config/roles.yaml`:

```yaml
roles:
  developer:
    model: claude-3.5-sonnet
    providers: [claude_code, openrouter, groq]
    budget_limit: 10.00
```

## How Key Rotation Works

The Google AI Studio provider implements intelligent multi-key rotation:

1. **Round-Robin Strategy**: Cycles through configured API keys
2. **Automatic Failover**: On HTTP 429 (rate limit), immediately rotates to next key
3. **Cooldown Period**: Configurable delay (default 60s) between rotations
4. **Persistent State**: Key index stored in `.cache/google_ai_studio.keyidx`
5. **Graceful Degradation**: Falls back to fewer keys if some are invalid

See `config/READ_ME_KEY_ROTATION.md` for detailed implementation notes.

## Per-Model Rate Limits

The system enforces rate limits to prevent API quota exhaustion:

- **RPM (Requests Per Minute)**: Limits API call frequency
- **TPM (Tokens Per Minute)**: Limits token consumption
- **Sliding Window**: 60-second rolling window for accurate tracking
- **Smart Fallback**: Automatically tries next provider when limits hit
- **Sleep Strategy**: Optional waiting when limits exceeded

Rate limits are configured per provider and model in `config/limits.yaml`.

## Available Commands

```bash
# Development
make setup          # Install dependencies
make run            # Run the main CLI
make bot            # Start Discord bot
make watch          # Watch for changes
make lint           # Run linting
make test           # Run tests

# Production
make build          # Build for production
make deploy         # Deploy to production
```

## Project Structure

```
nexus-cli/
├── config/           # Configuration files
│   ├── models.yaml   # Provider and model definitions
│   ├── roles.yaml    # AI role configurations
│   ├── limits.yaml   # Rate limiting rules
│   └── settings.toml # General settings
├── connectors/       # Provider integrations
│   ├── providers/    # AI model providers
│   ├── discord/      # Discord bot
│   └── vault/        # Obsidian integration
├── core/             # Core routing logic
│   ├── router.py     # Provider routing
│   ├── rate_limiter.py # Rate limiting
│   └── config.py     # Configuration management
├── tasks/            # Task definitions
├── tests/            # Test suite
└── utils/            # Utility functions
```

## Development

### Adding a New Provider

1. Create provider class in `connectors/providers/`
2. Add provider to `config/models.yaml`
3. Update `core/router.py` provider map
4. Add rate limits to `config/limits.yaml`
5. Write tests in `tests/`

### Running Tests

```bash
make test                    # Run all tests
python -m pytest tests/     # Direct pytest
```

## Troubleshooting

### Google AI Studio Key Rotation Issues

- Check `.cache/google_ai_studio.keyidx` for current key index
- Verify all 5 `GOOGLE_API_KEY_*` environment variables
- Review logs for rotation events and quota errors

### Rate Limiting Problems

- Check `config/limits.yaml` for model-specific limits
- Monitor logs for rate limit warnings
- Adjust RPM/TPM values based on your API quotas

### Provider Connection Issues

- Verify API keys in `.env`
- Check provider availability with `make test`
- Review network connectivity and firewall settings

## License

[License information here]

## Contributing

[Contributing guidelines here]