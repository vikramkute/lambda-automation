# API Gateway REST API
resource "aws_api_gateway_rest_api" "lambda_api" {
  name        = "lambda-automation-api"
  description = "API Gateway for Lambda functions"

  lifecycle {
    prevent_destroy = false
    ignore_changes  = []
  }
}

# Local variable for functions with API Gateway enabled
locals {
  api_functions = {
    for name, config in local.function_list :
    name => config if try(config.api_gateway_enabled, false) == true
  }
}

# API Gateway Resources (dynamic)
resource "aws_api_gateway_resource" "function_resource" {
  for_each    = local.api_functions
  rest_api_id = aws_api_gateway_rest_api.lambda_api.id
  parent_id   = aws_api_gateway_rest_api.lambda_api.root_resource_id
  path_part   = replace(lower(each.key), "_", "-")
}

# API Gateway Methods - GET (dynamic)
resource "aws_api_gateway_method" "function_method_get" {
  for_each      = local.api_functions
  rest_api_id   = aws_api_gateway_rest_api.lambda_api.id
  resource_id   = aws_api_gateway_resource.function_resource[each.key].id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Methods - POST (dynamic)
resource "aws_api_gateway_method" "function_method_post" {
  for_each      = local.api_functions
  rest_api_id   = aws_api_gateway_rest_api.lambda_api.id
  resource_id   = aws_api_gateway_resource.function_resource[each.key].id
  http_method   = "POST"
  authorization = "NONE"
}

# Lambda Integrations - GET (dynamic)
resource "aws_api_gateway_integration" "function_integration_get" {
  for_each                = local.api_functions
  rest_api_id             = aws_api_gateway_rest_api.lambda_api.id
  resource_id             = aws_api_gateway_resource.function_resource[each.key].id
  http_method             = aws_api_gateway_method.function_method_get[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.functions[each.key].invoke_arn
}

# Lambda Integrations - POST (dynamic)
resource "aws_api_gateway_integration" "function_integration_post" {
  for_each                = local.api_functions
  rest_api_id             = aws_api_gateway_rest_api.lambda_api.id
  resource_id             = aws_api_gateway_resource.function_resource[each.key].id
  http_method             = aws_api_gateway_method.function_method_post[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.functions[each.key].invoke_arn
}

# Lambda Permissions for API Gateway (dynamic)
resource "aws_lambda_permission" "api_gateway_invoke" {
  for_each      = local.api_functions
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.lambda_api.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "lambda_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.lambda_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.function_integration_get,
      aws_api_gateway_integration.function_integration_post
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.lambda_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.lambda_api.id
  stage_name    = "prod"
}

# Outputs
output "api_gateway_url" {
  description = "API Gateway endpoint URLs"
  value = {
    for name in keys(local.api_functions) :
    name => "${aws_api_gateway_stage.prod.invoke_url}/${replace(lower(name), "_", "-")}"
  }
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.lambda_api.id
}
