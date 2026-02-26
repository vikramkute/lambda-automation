# Download Lambda Functions

This guide describes how to download multiple AWS Lambda functions as ZIP files.

## Prerequisites

- AWS credentials available via environment or AWS CLI config.
- Python dependencies installed (see requirements.txt).

## Script

Use [download_lambda_functions.py](download_lambda_functions.py) to download function code.

## Examples

```bash
# Download specific functions
python download_lambda_functions.py --functions myTestFunction1,myTestFunction2 --out exported

# Download enabled functions from functions.config.yaml
python download_lambda_functions.py --out exported

# Keep ZIP files only (no extraction)
python download_lambda_functions.py --functions myTestFunction1,myTestFunction2 --no-extract
```

## Output

The output folder contains one subfolder per function, with:

- The function ZIP file
- Optional extracted code folder (code/)

## Notes

- Use `--region` to override the AWS region if needed
- Use `--no-extract` to keep ZIP files only without extracting
- If a function name is not found, the script logs an error and continues.
