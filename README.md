# Canas Construction API

A production-ready FastAPI application designed with AWS deployment best practices.

## Features

- FastAPI framework with async support
- Docker containerization with multi-stage builds
- AWS-ready infrastructure (ECS, RDS, ElastiCache, ECR)
- Health check endpoints for AWS load balancers
- Structured logging with CloudWatch integration
- Environment-based configuration
- Database migrations with Alembic
- Security best practices (JWT, password hashing)
- CORS and middleware configuration

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── health.py          # Health check endpoints
│   │   └── routes.py           # API router configuration
│   ├── core/
│   │   ├── config.py           # Application settings
│   │   ├── logging.py          # Logging configuration
│   │   └── security.py         # Security utilities
│   └── main.py                 # FastAPI application entry point
├── aws/
│   ├── buildspec.yml           # AWS CodeBuild configuration
│   ├── cloudformation-infrastructure.yml  # CloudFormation template
│   └── ecs-task-definition.json          # ECS task definition
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Local development setup
├── alembic.ini                 # Database migration config
└── Makefile                    # Common commands

```

## Local Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- PostgreSQL (if not using Docker)
- Redis (optional)

### Setup

1. Clone the repository and navigate to the project directory

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make dev-install
# or
pip install -r requirements-dev.txt
```

4. Copy environment variables:
```bash
cp .env.example .env
```

5. Update `.env` with your local configuration

### Running Locally

**Without Docker:**
```bash
make run
# or
uvicorn app.main:app --reload
```

**With Docker:**
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/api/v1/docs`
- Health Check: `http://localhost:8000/api/v1/health`

## Testing

```bash
make test
# or
pytest tests/ -v --cov=app
```

## AWS Deployment

### Deployment Options

This API supports multiple AWS deployment methods:

1. **AWS ECS (Fargate)** - Recommended for production
2. **AWS Lambda** - Serverless option using Mangum
3. **AWS Elastic Beanstalk** - Managed platform
4. **AWS EC2** - Traditional compute

### Option 1: ECS Fargate (Recommended)

#### Prerequisites

- AWS CLI configured
- AWS account with appropriate permissions
- Docker installed locally

#### Step 1: Create Infrastructure

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name canas-construction-infrastructure \
  --template-body file://aws/cloudformation-infrastructure.yml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=production \
    ParameterKey=DBUsername,ParameterValue=postgres \
    ParameterKey=DBPassword,ParameterValue=YOUR_SECURE_PASSWORD \
  --capabilities CAPABILITY_IAM
```

#### Step 2: Build and Push Docker Image

```bash
# Get your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push
docker build -t canas-construction-api .
docker tag canas-construction-api:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/canas-construction-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/canas-construction-api:latest
```

#### Step 3: Create Secrets in AWS Secrets Manager

```bash
# Database URL
aws secretsmanager create-secret \
  --name canas-construction/database-url \
  --secret-string "postgresql://user:pass@your-rds-endpoint:5432/dbname"

# Secret Key
aws secretsmanager create-secret \
  --name canas-construction/secret-key \
  --secret-string "your-secret-key-here"
```

#### Step 4: Update ECS Task Definition

Update `aws/ecs-task-definition.json` with:
- Your AWS Account ID
- Your ECR image URI
- Correct ARNs for secrets

#### Step 5: Register Task Definition and Create Service

```bash
# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://aws/ecs-task-definition.json

# Create ECS service (you'll need to create ALB first)
aws ecs create-service \
  --cluster production-cluster \
  --service-name canas-construction-api \
  --task-definition canas-construction-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:region:account-id:targetgroup/xxx,containerName=canas-construction-api,containerPort=8000"
```

### Option 2: AWS Lambda (Serverless)

The application includes Mangum handler for Lambda deployment.

1. Install dependencies in a package directory
2. Create deployment package with your code
3. Upload to Lambda
4. Configure API Gateway

```bash
# Package for Lambda
mkdir package
pip install -r requirements.txt -t package/
cp -r app package/
cd package && zip -r ../deployment.zip . && cd ..
```

### Option 3: Using AWS CodePipeline

For CI/CD, set up:

1. **CodeCommit/GitHub** - Source repository
2. **CodeBuild** - Uses `aws/buildspec.yml`
3. **CodeDeploy** - Deploys to ECS

The buildspec.yml is already configured for this workflow.

## Environment Variables for AWS

Key environment variables for production:

```bash
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/db
REDIS_URL=redis://elasticache-endpoint:6379/0
SECRET_KEY=your-secret-key
AWS_REGION=us-east-1
CORS_ORIGINS=["https://yourdomain.com"]
LOG_LEVEL=INFO
```

## AWS Best Practices Implemented

1. **Security**
   - Secrets stored in AWS Secrets Manager
   - Non-root user in Docker container
   - Security groups with least privilege
   - Encrypted RDS storage

2. **High Availability**
   - Multi-AZ RDS deployment
   - ECS tasks across multiple availability zones
   - Auto-scaling configuration ready

3. **Monitoring**
   - CloudWatch logs integration
   - Health check endpoints
   - Structured JSON logging

4. **Cost Optimization**
   - Fargate Spot option available
   - ECR lifecycle policies
   - Right-sized container resources

5. **Performance**
   - Multi-stage Docker builds
   - Connection pooling for database
   - Redis caching ready
   - GZip compression middleware

## Health Checks

- `/api/v1/health` - Basic health check (for ALB)
- `/api/v1/health/ready` - Readiness probe
- `/api/v1/health/live` - Liveness probe

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring and Logs

Logs are automatically sent to CloudWatch in production. View them:

```bash
aws logs tail /ecs/canas-construction-api --follow
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `make test`
4. Submit a pull request

## License

MIT
