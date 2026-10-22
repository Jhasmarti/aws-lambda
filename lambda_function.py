"""
Description: Simulates an AWS Lambda function triggered by an S3 ObjectCreated event.
             Reads a text file, calculates line/word/character metrics,
             and outputs a structured JSON result.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
import urllib.parse

# ---------------------------------------------------------------------------
# Structured Logging Setup (Simulates AWS CloudWatch Logs)
# ---------------------------------------------------------------------------
logger = logging.getLogger("S3FileProcessor")
logger.setLevel(logging.INFO)

# Agar handler pehle se set nahi hai toh standard stream handler add karo
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [RequestID: %(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class RequestContextFilter(logging.Filter):
    """Log messages mein dynamic AWS Request ID inject karne ke liye filter"""
    def __init__(self, request_id="LOCAL-SIM-001"):
        super().__init__()
        self.request_id = request_id

    def filter(self, record):
        record.request_id = self.request_id
        return True


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def validate_s3_event(event: dict) -> tuple[str, str]:
    """
    Validates S3 event schema and extracts bucket_name and object_key.
    Raises ValueError if event structure is malformed.
    """
    if not isinstance(event, dict):
        raise ValueError("Invalid event: Event must be a dictionary.")

    records = event.get("Records")
    if not records or not isinstance(records, list) or len(records) == 0:
        raise ValueError("Invalid event: 'Records' list is missing or empty.")

    first_record = records[0]
    s3_data = first_record.get("s3")
    if not s3_data:
        raise ValueError("Invalid event: Missing 's3' key in Records[0].")

    bucket_name = s3_data.get("bucket", {}).get("name")
    raw_key = s3_data.get("object", {}).get("key")

    if not bucket_name or not raw_key:
        raise ValueError("Invalid event: Missing bucket name or object key.")

    # S3 keys URL-encoded ho sakti hain (e.g. spaces as '+' or '%20')
    object_key = urllib.parse.unquote_plus(raw_key)
    return bucket_name, object_key


def process_file_metrics(file_path: str) -> dict:
    """
    Reads the file from disk and calculates lines, words, characters,
    longest word, and uppercase count.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    words = content.split()
    total_chars = len(content)
    total_chars_no_spaces = len("".join(words))

    # ⭐ NAYA CUSTOM LOGIC IMPLEMENT KIYA:
    longest_word = max(words, key=len) if words else ""
    uppercase_count = sum(1 for char in content if char.isupper())

    return {
        "line_count": len(lines),
        "word_count": len(words),
        "character_count_raw": total_chars,
        "character_count_no_whitespace": total_chars_no_spaces,
        "longest_word": longest_word,           # <-- Naya metric
        "uppercase_letters_count": uppercase_count # <-- Naya metric
    }


# ---------------------------------------------------------------------------
# Main AWS Lambda Handler
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """
    Standard AWS Lambda entry point.
    Parameters:
      - event: S3 ObjectCreated event dictionary.
      - context: AWS Lambda Context object (or mock context).
    Returns:
      - API-compatible response dictionary with statusCode and JSON body.
    """
    # Request ID extract karo (real Lambda context mein aws_request_id attribute hota hai)
    request_id = getattr(context, "aws_request_id", "LOCAL-REQ-DEFAULT")

    # Logging filter apply karo
    context_filter = RequestContextFilter(request_id)
    logger.addFilter(context_filter)

    try:
        logger.info("Lambda invocation started.")

        # Step 1: Validate event payload
        bucket_name, object_key = validate_s3_event(event)
        logger.info(f"Received S3 event for Bucket: '{bucket_name}', Object Key: '{object_key}'.")

        # Step 2: Validate file extension (Only text files supported)
        allowed_extensions = (".txt", ".log", ".csv", ".json")
        _, ext = os.path.splitext(object_key.lower())
        if ext not in allowed_extensions:
            error_msg = f"Unsupported file extension '{ext}'. Only {allowed_extensions} are processed."
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"status": "FAILED", "error": error_msg, "requestId": request_id})
            }

        # Step 3: Locate file path (Simulating S3 GetObject)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_file_path = os.path.join(base_dir, object_key)

        if not os.path.exists(local_file_path):
            error_msg = f"File '{object_key}' not found at path: {local_file_path}"
            logger.error(error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"status": "FAILED", "error": error_msg, "requestId": request_id})
            }

        logger.info(f"Reading file '{object_key}'...")
        metrics = process_file_metrics(local_file_path)
        logger.info(f"Processing complete: {metrics['line_count']} lines, {metrics['word_count']} words, {metrics['character_count_raw']} chars.")

        # Step 4: Prepare output summary (Simulating S3 PutObject)
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        result_file_path = os.path.join(output_dir, "result.json")

        result_payload = {
            "execution_status": "SUCCESS",
            "request_id": request_id,
            "processed_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": {
                "bucket": bucket_name,
                "key": object_key
            },
            "metrics": metrics
        }

        with open(result_file_path, "w", encoding="utf-8") as out_f:
            json.dump(result_payload, out_f, indent=4)

        logger.info(f"Result summary successfully written to: {result_file_path}")

        return {
            "statusCode": 200,
            "body": json.dumps(result_payload)
        }

    except ValueError as ve:
        logger.error(f"Validation Error: {str(ve)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "FAILED", "error": str(ve), "requestId": request_id})
        }
    except Exception as exc:
        logger.exception(f"Unexpected error during processing: {str(exc)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "FAILED", "error": str(exc), "requestId": request_id})
        }
    finally:
        logger.removeFilter(context_filter)