# Quick Start Guide

## Get Started in 5 Minutes

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set at minimum:
# - DATABASE_URL
# - SECRET_KEY (use: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 3. Run with Docker (Easiest)

```bash
# Start all services (API + PostgreSQL + Redis)
docker-compose up

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/api/v1/docs
```

### 4. Run without Docker

```bash
# Make sure PostgreSQL is running locally
# Update DATABASE_URL in .env

# Run the API
uvicorn app.main:app --reload

# Access at http://localhost:8000
```

## Test the API

```bash
# Check health
curl http://localhost:8000/api/v1/health

# View interactive docs
open http://localhost:8000/api/v1/docs
```

## Next Steps

1. Add your business logic in `app/services/`
2. Create data models in `app/models/`
3. Add API routes in `app/api/`
4. Write tests in `tests/`

## Common Commands

```bash
# Run tests
pytest

# Format code
black app/

# Run linter
flake8 app/

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## AWS Deployment

When ready to deploy to AWS, see the detailed instructions in README.md.

Key steps:
1. Deploy CloudFormation infrastructure
2. Build and push Docker image to ECR
3. Create ECS service
4. Configure secrets in AWS Secrets Manager

## Troubleshooting

**Can't connect to database?**
- Check DATABASE_URL in .env
- Ensure PostgreSQL is running
- With Docker: `docker-compose logs db`

**Import errors?**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**Port already in use?**
- Change PORT in .env or docker-compose.yml
- Kill existing process: `lsof -ti:8000 | xargs kill`
