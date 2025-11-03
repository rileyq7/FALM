# Terraform Variables for FALM

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "task_cpu" {
  description = "CPU units for ECS task"
  type        = string
  default     = "1024"  # 1 vCPU
}

variable "task_memory" {
  description = "Memory for ECS task (MB)"
  type        = string
  default     = "2048"  # 2GB
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "chromadb_mode" {
  description = "ChromaDB mode: local or cloud"
  type        = string
  default     = "cloud"
}

variable "chromadb_cloud_url" {
  description = "ChromaDB Cloud URL"
  type        = string
  sensitive   = true
}

variable "chromadb_api_key" {
  description = "ChromaDB API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "mongodb_url" {
  description = "MongoDB Atlas connection string"
  type        = string
  default     = "mongodb+srv://..."
}

variable "s3_bucket_name" {
  description = "S3 bucket for grant storage"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = ""
}
