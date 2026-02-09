# EventBridge Scheduler for Lambda functions
resource "aws_scheduler_schedule" "mytestfunction2_schedule" {
  name       = "MyTestSchedule2"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "at(2026-02-09T16:10:00)"

  target {
    arn      = aws_lambda_function.functions["myTestFunction2"].arn
    role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_ab1d2ce30c"

    input = jsonencode({
      source      = "aws.scheduler"
      detail-type = "Scheduled Event"
      detail = {
        message = "Test scheduler event"
      }
    })
  }
}

# Lambda permission for EventBridge Scheduler
resource "aws_lambda_permission" "scheduler_invoke_mytestfunction2" {
  statement_id  = "AllowEventBridgeSchedulerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions["myTestFunction2"].function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule/default/MyTestSchedule2"
}


