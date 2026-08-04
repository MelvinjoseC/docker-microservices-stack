variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "devops-microservices-cluster"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}
