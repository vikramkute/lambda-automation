terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Use default AWS credentials from environment or AWS CLI config
# Credentials should be provided via environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# or AWS CLI configuration, NOT through Terraform variables
provider "aws" {
  region = var.aws_region
}

# Data source for AWS account ID
data "aws_caller_identity" "current" {}