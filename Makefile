.PHONY: install dev mcp build test audit

install:
	python -m pip install -e .
	cd web && npm install

dev:
	@echo "Run 'captivity-simulator' and 'cd web && npm run dev' in separate terminals."

mcp:
	captivity-simulator-mcp

build:
	cd web && npm run build

test:
	python -m unittest discover -s tests -v

audit:
	python scripts/audit_open_source.py
