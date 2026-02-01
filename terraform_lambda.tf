# Variables for Lambda function configuration
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "lambda_functions" {
  description = "Configuration for Lambda functions"
  type = map(object({
    runtime         = string
    memory          = number
    timeout         = number
    environment     = optional(map(string))
    description     = optional(string)
  }))
  default = {}
}

variable "lambda_iam_role_name" {
  description = "IAM role for Lambda functions"
  type        = string
  default     = "LambdaFullAccessForS3Role"
}


# Local variables for common settings
locals {
  function_list = var.lambda_functions
  common_tags = {
    Project     = "lambda-automation"
    ManagedBy   = "Terraform"
    UpdatedAt   = formatdate("YYYY-MM-DD", timestamp())
  }
}

# Data source for existing IAM role
data "aws_iam_role" "lambda_role" {
  name = var.lambda_iam_role_name
}

# Lambda functions - created from configuration
resource "aws_lambda_function" "functions" {
  for_each = local.function_list
  filename      = ".packages/${each.key}.zip"
  function_name = each.key
  role          = data.aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = each.value.runtime
  memory_size = each.value.memory
  timeout     = each.value.timeout
  description   = each.value.description

  # Only add environment block if environment variables exist and don't contain reserved keys
  dynamic "environment" {
    for_each = length(each.value.environment) > 0 ? [1] : []
    content {
      variables = {
        for k, v in each.value.environment : k => v
        if !contains(["AWS_REGION", "AWS_DEFAULT_REGION", "AWS_LAMBDA_FUNCTION_NAME", "AWS_LAMBDA_FUNCTION_VERSION", "AWS_LAMBDA_LOG_GROUP_NAME", "AWS_LAMBDA_LOG_STREAM_NAME"], k)
      }
    }
  }

  tags = merge(
    local.common_tags,
    {
      Function        = each.key
      Runtime         = each.value.runtime
      MemorySize      = each.value.memory
      TimeoutSeconds  = each.value.timeout
    }
  )
}

# Outputs
output "lambda_function_arns" {
  description = "ARNs of deployed Lambda functions"
  value = {
    for name, func in aws_lambda_function.functions :
    name => func.arn
  }
}

output "lambda_function_names" {
  description = "Names of deployed Lambda functions"
  value = {
    for name, func in aws_lambda_function.functions :
    name => func.function_name
  }
}