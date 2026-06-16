.PHONY: up down logs demo test

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

demo:
	docker compose rm -sf demo
	docker compose up --build --no-deps demo

test:
	python -m pytest -q --cov=agent --cov=analyzer --cov-report=term-missing
