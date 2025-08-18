SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
export PYTHONPATH := src:$(PYTHONPATH)

.PHONY: setup run bot watch lint test envcheck loopcheck fix-env which-bash

setup:
	python -m venv .venv
	. .venv/bin/activate
	pip install -U pip setuptools wheel
	pip install -e .

run:
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	python -m nexuscli.orchestrator

bot:
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	python -m connectors.discord.bot

# Fast demo: shorter responses, fewer roles
.PHONY: fast-bot
fast-bot:
	@echo "Starting fast bot (short outputs, fewer roles)..."
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	OPENROUTER_MAX_TOKENS?=400; ORCHESTRATOR_ROLES?=communications,senior_dev; \
	OPENROUTER_MAX_TOKENS=$$OPENROUTER_MAX_TOKENS ORCHESTRATOR_ROLES=$$ORCHESTRATOR_ROLES \
	python -m connectors.discord.bot

watch:
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	python -m core.orchestrator

lint:
	. .venv/bin/activate
	ruff check .

test:
	. .venv/bin/activate
	pytest -q

which-bash:
	@echo "SHELL=$(SHELL)"
	@$(SHELL) -lc 'command -v bash && bash --version | head -1'

fix-env:
	@if [ -f .env ]; then sed -i 's/\r$//' .env; echo "Normalized .env"; fi

envcheck:
	@echo "Environment quick check (masked)"
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	./.venv/bin/python -c 'import os,sys; mask=lambda s:(s if not s else (s[:4]+"…"+s[-4:] if len(s)>8 else "****")); keys=["DISCORD_BOT_TOKEN","DISCORD_APP_ID","DISCORD_GUILD_ID","DISCORD_COMMANDS_CHANNEL_ID","DISCORD_UPDATES_CHANNEL_ID","COMMUNICATIONS_WEBHOOK_URL","PM_WEBHOOK_URL","SD_WEBHOOK_URL","JD_WEBHOOK_URL","RQE_WEBHOOK_URL"]; [print(f"{k:30} = {mask(os.getenv(k))}") for k in keys]; print(f"USE_PAID_MODELS             = {os.getenv("USE_PAID_MODELS","true")}"); print(f"ALLOWED_MODEL_TIERS         = {os.getenv("ALLOWED_MODEL_TIERS","(derived from USE_PAID_MODELS)")}"); print(f"OPENROUTER_MAX_TOKENS       = {os.getenv("OPENROUTER_MAX_TOKENS","800")}"); print(f"ORCHESTRATOR_ROLES          = {os.getenv("ORCHESTRATOR_ROLES","communications,project_manager,senior_dev,junior_dev,release_qa")}"); print(f"DISCORD_MESSAGE_CONTENT     = {os.getenv("DISCORD_MESSAGE_CONTENT","0")}"); print(f"DISCORD_MEMBERS             = {os.getenv("DISCORD_MEMBERS","0")}"); print(f"DISCORD_PRESENCE            = {os.getenv("DISCORD_PRESENCE","0")}"); sys.path.insert(0,"src"); from core.config import ConfigManager; from core.router import ProviderRouter; pr=ProviderRouter(ConfigManager("config")); av=pr.get_available_providers(); print("AVAILABLE_PROVIDERS         =", ", ".join(av) if av else "None")'

loopcheck:
	@echo "Checking asyncio loop scheduling..."
	. .venv/bin/activate
	./.venv/bin/python -c 'import asyncio, threading; loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); fut=loop.create_future(); threading.Thread(target=lambda: loop.call_soon_threadsafe(fut.set_result, "ok"), daemon=True).start(); loop.run_until_complete(fut); print("Loopcheck:", "OK" if fut.result()=="ok" else "Unexpected")'
