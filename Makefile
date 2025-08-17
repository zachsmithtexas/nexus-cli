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
	mkdir -p scripts
		cat > scripts/.envcheck.py <<- 'PY'
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
	. .venv/bin/activate
	set -a; [ -f .env ] && . ./.env || true; set +a
	./.venv/bin/python scripts/.envcheck.py
	rm -f scripts/.envcheck.py

loopcheck:
	@echo "Checking asyncio loop scheduling..."
	mkdir -p scripts
		cat > scripts/.loopcheck.py <<- 'PY'
		import sys, pathlib, asyncio, threading
		from pathlib import Path
		# Ensure src layout import if package not installed
		sys.path.insert(0, str(pathlib.Path("src").resolve()))
		try:
		    from core.orchestrator import Orchestrator
		except Exception:
		    Orchestrator = None

		async def main():
		    loop = asyncio.get_running_loop()
		    if Orchestrator:
		        _ = Orchestrator(Path.cwd(), loop=loop)
		    async def coro():
		        print("✅ scheduled on", asyncio.get_running_loop())
		    def other_thread():
		        loop.call_soon_threadsafe(asyncio.create_task, coro())
		    threading.Thread(target=other_thread, daemon=True).start()
		    await asyncio.sleep(0.2)

		asyncio.run(main())
		PY
	. .venv/bin/activate
	./.venv/bin/python scripts/.loopcheck.py
	rm -f scripts/.loopcheck.py
