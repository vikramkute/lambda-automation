@echo off
REM AWS Lambda Automation Framework - Windows Batch Wrapper
REM This allows running commands like: run.bat upgrade, run.bat test, etc.

setlocal enabledelayedexpansion

if "%1"=="" (
    echo AWS Lambda Automation Framework - Windows Batch Runner
    echo.
    echo Usage: run.bat [command]
    echo.
    echo Examples:
    echo   run.bat setup                 - Setup environment
    echo   run.bat help                  - Show all commands
    echo   run.bat install-deps          - Install Python dependencies
    echo   run.bat validate-config       - Validate configuration
    echo   run.bat list-functions        - List configured functions
    echo   run.bat check-runtime-version - Check runtime versions
    echo   run.bat upgrade               - Upgrade to latest Python
    echo   run.bat test                  - Run tests
    echo   run.bat test-fast             - Quick tests
    echo   run.bat build                 - Build functions
    echo   run.bat compare [f1] [f2]     - Compare two Lambda functions
    echo   run.bat compare-config        - Compare functions from comparison.config.yaml
    echo   run.bat compare-ast [f1] [f2] - Compare functions at AST level
    echo   run.bat compare-ast-config    - AST compare from comparison.config.yaml
    echo   run.bat report                - Generate HTML comparison report for AST comparisons
    echo   run.bat init-terraform        - Initialize Terraform
    echo   run.bat create-log-groups     - Create CloudWatch log groups
    echo   run.bat terraform-output      - Show Terraform outputs
    echo   run.bat plan-deploy           - Plan deployment
    echo   run.bat deploy                - Complete deployment
    echo   run.bat delete-function [name] - Delete specific Lambda function
    echo   run.bat destroy-infra         - Destroy AWS resources
    echo   run.bat clean                 - Clean artifacts
    echo   run.bat full-pipeline         - Execute complete pipeline
    echo.
    echo For more info, see README.md or run: powershell -NoProfile .\run.ps1 help
    exit /b 0
)

REM Run PowerShell script with the command and optional parameters
if "%3"=="" (
    if "%2"=="" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\run.ps1' -Command '%1' -ScriptName 'run.bat'"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\run.ps1' -Command '%1' -FunctionList '%2' -ScriptName 'run.bat'"
    )
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\run.ps1' -Command '%1' -FunctionList '%2' -Function2 '%3' -ScriptName 'run.bat'"
)
exit /b %ERRORLEVEL%
