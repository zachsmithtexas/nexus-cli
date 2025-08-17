# Makefile for Nexus CLI
.ONESHELL:
SHELL := /usr/bin/env bash
.PHONY: help venv setup run bot watch lint test clean install dev demo status envcheck fix-env

# Default target
help:
	@echo "Nexus CLI - Local-first 5-agent development stack"
	@echo ""
	@echo "Available targets:"
	@echo "  setup     - Install dependencies and set up environment"
	@echo "  run       - Start the main orchestrator"
	@echo "  bot       - Start the Discord bot"
	@echo "  watch     - Start file watching mode"
	@echo "  lint      - Run code linting"
	@echo "  test      - Run unit tests"
	@echo "  demo      - Run demonstration workflow"
	@echo "  install   - Install package in development mode"
	@echo "  dev       - Start development environment"
	@echo "  clean     - Clean up temporary files"
	@echo ""
	@echo "Configuration:"
	@echo "  Copy .env.example to .env and configure your settings"
	@echo ""

# Create virtual environment
venv:
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		if command -v python3 >/dev/null 2>&1; then \
			python3 -m venv .venv || { \
				echo ""; \
				echo "❌ Virtual environment creation failed."; \
				echo "💡 On Debian/Ubuntu, try: sudo apt-get install -y python3-venv"; \
				echo ""; \
				exit 1; \
			}; \
		else \
			python -m venv .venv || { \
				echo ""; \
				echo "❌ Virtual environment creation failed."; \
				echo "💡 On Debian/Ubuntu, try: sudo apt-get install -y python3-venv"; \
				echo ""; \
				exit 1; \
			}; \
		fi; \
		echo "✅ Virtual environment created"; \
	else \
		echo "✅ Virtual environment already exists"; \
	fi

# Set up the environment
setup: venv
	@echo "Setting up Nexus CLI environment..."
	./.venv/bin/python -m pip install --upgrade pip
	./.venv/bin/python -m pip install -r requirements.txt
	./.venv/bin/python -m pip install -e .
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file - please configure it"; fi
	@mkdir -p tasks/{inbox,backlog,sprint,done}
	@mkdir -p vault/inbox/feedback
	@mkdir -p docs releases/v0.001
	@echo "Setup complete! Please configure your .env file."

# Install package in development mode (alias for setup)
install: setup
	@echo "Installation complete!"

# Start the main orchestrator
run:
	@echo "Starting Nexus CLI Orchestrator..."
	set -a; [ -f .env ] && source .env || true; set +a; \
	./.venv/bin/python -m core.orchestrator

# Start the Discord bot
bot:
	@echo "Starting Discord bot..."
	set -a; [ -f .env ] && source .env || true; set +a; \
	./.venv/bin/python -m connectors.discord.bot

# Start file watching mode (same as run, but with explicit messaging)
watch:
	@echo "Starting file watching mode..."
	@echo "Watching tasks/inbox for new task files..."
	./.venv/bin/python -m core.orchestrator

# Run code linting
lint:
	@echo "Running code linting..."
	./.venv/bin/python -m ruff check . --fix || echo "ruff not installed, skipping format check"
	./.venv/bin/python -m ruff format . || echo "ruff not installed, skipping format"
	@echo "Linting complete!"

# Run unit tests
test:
	@echo "Running unit tests..."
	./.venv/bin/python -m pytest tests/ -v --tb=short || echo "pytest not installed or no tests found"
	@echo ""
	@echo "Running agent tests..."
	./.venv/bin/python -m agents.junior_dev.main test
	@echo "Tests complete!"

# Show current status
status:
	@echo "Checking system status..."
	./.venv/bin/python scripts/print_status.py

# Run demonstration workflow
demo:
	@echo "Running Nexus CLI demonstration..."
	@echo ""
	@echo "1. Creating demonstration task..."
	./.venv/bin/python -m agents.communications.main process_idea "Implement utility function for string slugification"
	@echo ""
	@echo "2. Running junior dev implementation..."
	./.venv/bin/python -m agents.junior_dev.main demo
	@echo ""
	@echo "3. Creating release documentation..."
	./.venv/bin/python -m agents.release_qa.main create_release v0.001
	@echo ""
	@echo "4. Checking system status..."
	./.venv/bin/python scripts/print_status.py
	@echo ""
	@echo "Demo complete! Check the tasks/ and releases/ directories for results."

# Development mode - start orchestrator with debug logging
dev:
	@echo "Starting development environment..."
	@echo "Environment: Development"
	@echo "Log Level: DEBUG"
	LOG_LEVEL=DEBUG ./.venv/bin/python -m core.orchestrator

# Clean up temporary files
clean:
	@echo "Cleaning up temporary files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"


# Quick start - setup and run demo
quickstart: setup demo
	@echo ""
	@echo "🎉 Nexus CLI quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Configure your .env file with API keys"
	@echo "  2. Run 'make bot' to start Discord integration"
	@echo "  3. Run 'make run' to start the orchestrator"
	@echo "  4. Use Discord commands or add files to tasks/inbox/"

# Development helpers
check-config:
	@echo "Checking configuration..."
	@python -c "from core.config import ConfigManager; cm = ConfigManager('config'); print('✅ Configuration valid')" 2>/dev/null || echo "❌ Configuration error"

check-providers:
	@echo "Checking provider availability..."
	@python -c "from core.router import ProviderRouter; from core.config import ConfigManager; r = ProviderRouter(ConfigManager('config')); print('Available providers:', r.get_available_providers())"

# Quick diagnostics (masked)
envcheck:
	@echo "Environment quick check (masked)"
	set -a; [ -f .env ] && source .env || true; set +a; \
	./.venv/bin/python - <<'PY'
	import os
	def mask(s):
	    return s if not s else (s[:4] + "…" + s[-4:] if len(s) > 8 else "****")
	keys = [
	    "DISCORD_BOT_TOKEN",
	    "DISCORD_APP_ID","DISCORD_GUILD_ID",
	    "DISCORD_COMMANDS_CHANNEL_ID","DISCORD_UPDATES_CHANNEL_ID",
	    "COMMUNICATIONS_WEBHOOK_URL","PM_WEBHOOK_URL","SD_WEBHOOK_URL","JD_WEBHOOK_URL","RQE_WEBHOOK_URL"
	]
	for k in keys:
	    print(f"{k:30} = {mask(os.getenv(k))}")
	PY

# Normalize CRLF line endings in .env (WSL friendliness)
fix-env:
	@mkdir -p scripts
	@chmod +x scripts/fix-env.sh 2>/dev/null || true
	@./scripts/fix-env.sh 2>/dev/null || true

check-vault:
	@echo "Checking Obsidian vault integration..."
	@python -m connectors.vault.fs check

# Agent-specific commands
agent-comm:
	@echo "Testing Communications Agent..."
	@python -m agents.communications.main roadmap_summary

agent-pm:
	@echo "Testing Project Manager Agent..."
	@python -m agents.project_manager.main backlog_summary

agent-senior:
	@echo "Testing Senior Developer Agent..."
	@echo "No tasks to analyze currently"

agent-junior:
	@echo "Testing Junior Developer Agent..."
	@python -m agents.junior_dev.main test

agent-qa:
	@echo "Testing Release QA Agent..."
	@python -m agents.release_qa.main create_notes v0.001

# Create sample tasks for testing
create-sample-tasks:
	@echo "Creating sample tasks for testing..."
	@echo "---\ntitle: Sample Feature Request\nstatus: inbox\n---\n\n# Sample Feature Request\n\nImplement a new feature for user authentication." > tasks/inbox/sample_feature.md
	@echo "---\ntitle: Bug Fix Required\nstatus: inbox\n---\n\n# Bug Fix Required\n\nFix the login issue reported by users." > tasks/inbox/sample_bug.md
	@echo "---\ntitle: Documentation Update\nstatus: inbox\n---\n\n# Documentation Update\n\nUpdate the API documentation with new endpoints." > tasks/inbox/sample_docs.md
	@echo "Sample tasks created in tasks/inbox/"

# Backup and restore
backup:
	@echo "Creating backup..."
	@tar -czf nexus-cli-backup-$(shell date +%Y%m%d_%H%M%S).tar.gz tasks/ config/ docs/ releases/ vault/ --exclude='vault/inbox/feedback' 2>/dev/null || echo "Backup created (some directories may not exist yet)"

# Show logs (if implemented)
logs:
	@echo "Recent system activity:"
	@tail -20 nexus-cli.log 2>/dev/null || echo "No log file found. Logging may not be configured."

# Version info
version:
	@echo "Nexus CLI Version Information:"
	@echo "=============================="
	@python -c "import sys; print(f'Python: {sys.version}')"
	@pip show nexus-cli 2>/dev/null || echo "Package: Development version"
	@git describe --tags --always 2>/dev/null || echo "Git: Not a git repository"
