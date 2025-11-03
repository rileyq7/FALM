# AWS Deployment Guide

Complete guide to deploying FALM on AWS ECS Fargate with the full production pipeline.

## Architecture Overview

```
Internet → ALB (HTTPS) → ECS Fargate → ChromaDB Cloud
                ↓                  ↓
              WAF               MongoDB Atlas
                               S3 Buckets
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** installed (v1.0+)
4. **Docker** installed
5. **ChromaDB Cloud** account
6. **MongoDB Atlas** account (optional but recommended)

## Step-by-Step Deployment

### Step 1: Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### Step 2: Set Up External Services

#### ChromaDB Cloud

1. Go to https://www.trychroma.com/
2. Create account and project
3. Note credentials:
   - Instance URL: `your-instance.chromadb.io`
   - API Key: `chroma_xxx...`

#### MongoDB Atlas (Optional)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string: `mongodb+srv://...`
4. Whitelist AWS IP ranges

#### Anthropic API

1. Go to https://console.anthropic.com
2. Create API key
3. Note key: `sk-ant-...`

### Step 3: Build and Push Docker Image

```bash
# Navigate to project
cd /Users/rileycoleman/FALM

# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t falm:latest .

# Create ECR repository (if not exists)
aws ecr create-repository --repository-name falm --region us-east-1

# Tag image
docker tag falm:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/falm:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/falm:latest
```

### Step 4: Configure Terraform

```bash
cd deploy/terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**terraform.tfvars:**
```hcl
aws_region = "us-east-1"

# ECS
task_cpu      = "1024"
task_memory   = "2048"
desired_count = 2

# ChromaDB Cloud
chromadb_mode      = "cloud"
chromadb_cloud_url = "your-instance.chromadb.io"
chromadb_api_key   = "chroma_xxx..."

# Anthropic
anthropic_api_key = "sk-ant-..."

# MongoDB
mongodb_url = "mongodb+srv://user:pass@cluster.mongodb.net/falm"

# S3
s3_bucket_name = "falm-grants-yourname"
```

### Step 5: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy
terraform apply
# Type 'yes' to confirm
```

**This creates:**
- VPC with public/private subnets
- Application Load Balancer
- ECS Fargate cluster
- Auto-scaling configuration
- CloudWatch logging
- Secrets Manager entries
- S3 bucket
- Security groups

### Step 6: Get ALB DNS Name

```bash
terraform output alb_dns_name
# Output: falm-alb-1234567890.us-east-1.elb.amazonaws.com
```

### Step 7: Test Deployment

```bash
# Health check
curl http://<alb-dns-name>/

# Query API
curl -X POST "http://<alb-dns-name>/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants"}'

# View docs
open http://<alb-dns-name>/docs
```

### Step 8: Set Up Custom Domain (Optional)

#### Get SSL Certificate

```bash
# Request certificate in ACM
aws acm request-certificate \
  --domain-name grants.yourdomain.com \
  --validation-method DNS \
  --region us-east-1
```

#### Update Route 53

1. Create A record pointing to ALB
2. Add ACM certificate ARN to `terraform.tfvars`:
```hcl
acm_certificate_arn = "arn:aws:acm:us-east-1:123:certificate/..."
```

3. Re-apply Terraform:
```bash
terraform apply
```

Now accessible at: `https://grants.yourdomain.com`

## Monitoring

### CloudWatch Logs

```bash
# View logs
aws logs tail /ecs/falm --follow

# Filter errors
aws logs tail /ecs/falm --follow --filter-pattern "ERROR"
```

### CloudWatch Metrics

Go to AWS Console → CloudWatch → Dashboards

Key metrics:
- ECS CPU/Memory utilization
- ALB request count
- ALB target response time
- ECS task count

### Set Up Alarms

```bash
# CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name falm-high-cpu \
  --alarm-description "FALM CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Auto-Scaling

Already configured in Terraform:

- **Min tasks:** 1
- **Max tasks:** 10
- **Trigger:** CPU > 70%
- **Scale out:** Add 1 task
- **Scale in:** Remove 1 task (after 5 min cooldown)

## Cost Optimization

### Development

```hcl
# terraform.tfvars
desired_count = 1
min_capacity  = 0  # Scale to zero during off-hours
task_cpu      = "512"
task_memory   = "1024"
```

**Estimated cost:** ~$15-20/month

### Production

```hcl
desired_count = 2
min_capacity  = 2
max_capacity  = 10
task_cpu      = "1024"
task_memory   = "2048"
```

**Estimated cost:** ~$50-100/month (depending on traffic)

### Cost Breakdown

| Service | Monthly Cost |
|---------|--------------|
| ECS Fargate (2 tasks) | $30-40 |
| ALB | $16 |
| NAT Gateway | $32 |
| CloudWatch Logs | $5 |
| S3 | $1-5 |
| ChromaDB Cloud | Free-$29 |
| MongoDB Atlas | Free-$9 |
| **Total** | **~$84-131** |

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: falm
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster falm-cluster \
            --service falm-service \
            --force-new-deployment
```

## Troubleshooting

### Tasks Not Starting

```bash
# Check task logs
aws ecs describe-tasks \
  --cluster falm-cluster \
  --tasks $(aws ecs list-tasks --cluster falm-cluster --query 'taskArns[0]' --output text)

# Check service events
aws ecs describe-services \
  --cluster falm-cluster \
  --services falm-service
```

### Health Checks Failing

```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# View logs
aws logs tail /ecs/falm --follow
```

### High Costs

1. **Reduce task count:** Set `desired_count = 1`
2. **Smaller tasks:** Use `task_cpu = "512"`
3. **Remove NAT Gateway:** Use VPC endpoints instead
4. **Reduce log retention:** Set to 3 days

## Security Checklist

- [ ] Enable VPC Flow Logs
- [ ] Set up WAF rules on ALB
- [ ] Enable GuardDuty
- [ ] Rotate secrets regularly
- [ ] Use least-privilege IAM roles
- [ ] Enable MFA on AWS account
- [ ] Set up CloudTrail
- [ ] Review security groups monthly
- [ ] Enable S3 bucket encryption
- [ ] Use ACM for SSL certificates

## Backup Strategy

### ChromaDB

- Handled by ChromaDB Cloud (automatic backups)

### MongoDB

- Handled by MongoDB Atlas (automatic backups)

### S3 Grant Data

```bash
# Enable versioning (already in Terraform)
aws s3api put-bucket-versioning \
  --bucket falm-grants-yourname \
  --versioning-configuration Status=Enabled

# Enable cross-region replication
aws s3api put-bucket-replication \
  --bucket falm-grants-yourname \
  --replication-configuration file://replication.json
```

## Disaster Recovery

### RTO: 15 minutes
### RPO: 5 minutes

**Recovery Steps:**

1. **Total failure:**
```bash
cd deploy/terraform
terraform apply  # Rebuilds everything
```

2. **Data loss:**
- ChromaDB: Restore from cloud backup
- MongoDB: Restore from Atlas backup
- S3: Use versioning to recover

3. **Region failure:**
- Deploy to new region using same Terraform
- Update Route 53 to point to new ALB

## Next Steps

1. ✅ Deploy infrastructure
2. ✅ Test API endpoints
3. ✅ Set up monitoring alarms
4. 🔄 Add Lambda crawlers (see CRAWLER_SETUP.md)
5. 🔄 Build admin panel (see ADMIN_PANEL.md)
6. 🔄 Set up CI/CD pipeline

---

**Production deployment complete!** 🚀

Access your API at: `http://<alb-dns-name>/docs`
