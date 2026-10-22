"""
Description: Verifies business logic, event validation, file processing,
             and error handling using Python's built-in unittest module.
"""

import json
import os
import unittest
from lambda_function import lambda_handler, validate_s3_event, process_file_metrics


class MockContext:
    """Mock context object providing a test request ID"""
    def __init__(self, request_id="UNIT-TEST-REQ-001"):
        self.aws_request_id = request_id


class TestS3LambdaProcessor(unittest.TestCase):

    def setUp(self):
        """Runs before every test: creates a dedicated temp test file"""
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.context = MockContext()
        self.temp_filename = "unit_test_sample.txt"
        self.temp_filepath = os.path.join(self.test_dir, self.temp_filename)

        # 3 lines, 8 words:
        # Line 1: Alpha Beta Gamma (3 words)
        # Line 2: One Two Three (3 words)
        # Line 3: Four Five (2 words)
        with open(self.temp_filepath, "w", encoding="utf-8") as f:
            f.write("Alpha Beta Gamma\nOne Two Three\nFour Five\n")

    def tearDown(self):
        """Runs after every test: cleans up temp file"""
        if os.path.exists(self.temp_filepath):
            os.remove(self.temp_filepath)

    # -----------------------------------------------------------------------
    # Test 1: Event Validation - Happy Path
    # -----------------------------------------------------------------------
    def test_validate_s3_event_success(self):
        valid_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-key.txt"}
                    }
                }
            ]
        }
        bucket, key = validate_s3_event(valid_event)
        self.assertEqual(bucket, "test-bucket")
        self.assertEqual(key, "test-key.txt")

    # -----------------------------------------------------------------------
    # Test 2: Event Validation - Malformed Events
    # -----------------------------------------------------------------------
    def test_validate_s3_event_missing_records(self):
        with self.assertRaises(ValueError):
            validate_s3_event({})

        with self.assertRaises(ValueError):
            validate_s3_event({"Records": []})

    # -----------------------------------------------------------------------
    # Test 3: Metric Calculation Accuracy
    # -----------------------------------------------------------------------
    def test_process_file_metrics(self):
        metrics = process_file_metrics(self.temp_filepath)
        self.assertEqual(metrics["line_count"], 3)
        self.assertEqual(metrics["word_count"], 8)
        self.assertGreater(metrics["character_count_raw"], 0)
        self.assertGreater(metrics["character_count_no_whitespace"], 0)

    # -----------------------------------------------------------------------
    # Test 4: Full Handler Execution - 200 OK
    # -----------------------------------------------------------------------
    def test_handler_success(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": self.temp_filename}
                    }
                }
            ]
        }
        response = lambda_handler(event, self.context)
        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])
        self.assertEqual(body["execution_status"], "SUCCESS")
        self.assertEqual(body["metrics"]["line_count"], 3)
        self.assertEqual(body["metrics"]["word_count"], 8)

    # -----------------------------------------------------------------------
    # Test 5: Error Handling - Unsupported File Extension (400 Bad Request)
    # -----------------------------------------------------------------------
    def test_handler_unsupported_file_extension(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "malicious_script.exe"}
                    }
                }
            ]
        }
        response = lambda_handler(event, self.context)
        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])
        self.assertEqual(body["status"], "FAILED")
        self.assertIn("Unsupported file extension", body["error"])

    # -----------------------------------------------------------------------
    # Test 6: Error Handling - File Not Found (404 Not Found)
    # -----------------------------------------------------------------------
    def test_handler_file_not_found(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "missing_file.txt"}
                    }
                }
            ]
        }
        response = lambda_handler(event, self.context)
        self.assertEqual(response["statusCode"], 404)

        body = json.loads(response["body"])
        self.assertEqual(body["status"], "FAILED")
        self.assertIn("not found", body["error"])


if __name__ == "__main__":
    unittest.main()