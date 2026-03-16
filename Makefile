.PHONY: gui api cli streaks stars stack all sync-gui sync-api sync-cli sync-all test help

help:
	@echo "Available commands:"
	@echo "  make sync-all : Sync all dependencies (uv sync --all-extras)"
	@echo "  make gui      : Run the NEOSSat GUI"
	@echo "  make api      : Run the NEOSSat API"
	@echo "  make cli      : Run the NEOSSat CLI (pass args via ARGS=\"...\")"
	@echo "  make streaks  : Run the CLI with --streaks flag"
	@echo "  make stars    : Run the CLI with --stars flag"
	@echo "  make stack    : Run the CLI with --image-stacking flag"
	@echo "  make all      : Run the CLI with all tasks (stars, image stacking, and streaks)"
	@echo "  make test     : Run tests with pytest"

sync-all:
	uv sync --all-extras

gui:
	uv run --extra gui neossat-gui

api:
	uv run --extra api neossat-api

cli:
	uv run --extra cli neossat-cli $(ARGS)

streaks:
	uv run --extra cli neossat-cli --streaks

stars:
	uv run --extra cli neossat-cli --stars

stack:
	uv run --extra cli neossat-cli --image-stacking

all:
	uv run --extra cli neossat-cli --stars --streaks

test:
	uv run pytest

check:
	uv run black . 
	uv run isort .
	uv run flake8 . --exclude=.venv,__pycache__,.git,dl_streak_detect
