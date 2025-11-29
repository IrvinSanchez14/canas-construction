.PHONY: help install dev-install run test clean docker-build docker-run aws-ecr-login aws-push

help:
	@echo "Available commands:"
	@echo "  make install         - Install production dependencies"
	@echo "  make dev-install     - Install development dependencies"
	@echo "  make run            - Run the application locally"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean up temporary files"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container locally"
	@echo "  make aws-ecr-login  - Login to AWS ECR"
	@echo "  make aws-push       - Push Docker image to AWS ECR"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

docker-build:
	docker build -t canas-construction-api .

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down

aws-ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

aws-push:
	docker tag canas-construction-api:latest $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/canas-construction-api:latest
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/canas-construction-api:latest
