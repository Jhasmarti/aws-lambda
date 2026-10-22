"""

Description: Simulates the AWS Lambda execution environment.
             Loads test_event.json, creates a mock Lambda Context,
             invokes lambda_handler(event, context), and displays the results.
"""

import json
import os
import sys
import time
import uuid

# Import our Lambda handler
try:
    from lambda_function import lambda_handler
except ImportError as e:
    print(f"[ERROR] Could not import lambda_handler: {e}")
    sys.exit(1)


class MockLambdaContext:
    """
    Simulates the official AWS Lambda Context object.
    AWS Docs: https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    """
    def __init__(self, function_name="S3FileProcessorLocal", memory_limit_in_mb=128, timeout_seconds=30):
        self.function_name = function_name
        self.function_version = "$LATEST"
        self.invoked_function_arn = f"arn:aws:lambda:local:123456789012:function:{function_name}"
        self.memory_limit_in_mb = memory_limit_in_mb
        self.aws_request_id = str(uuid.uuid4())
        self.log_group_name = f"/aws/lambda/{function_name}"
        self.log_stream_name = f"2026/10/19/[$LATEST]{self.aws_request_id.replace('-', '')}"
        self._start_time = time.time()
        self._timeout = timeout_seconds

    def get_remaining_time_in_millis(self):
        elapsed = time.time() - self._start_time
        remaining = max(0, int((self._timeout - elapsed) * 1000))
        return remaining


def main():
   
    print(" STARTING LOCAL AWS LAMBDA SIMULATION")
   

    base_dir = os.path.dirname(os.path.abspath(__file__))
    event_path = os.path.join(base_dir, "test_event.json")

    if not os.path.exists(event_path):
        print(f"[ERROR] Test event file not found: {event_path}")
        sys.exit(1)

    # 1. Load the simulated S3 event
    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    # 2. Instantiate Mock Context (Simulates AWS Lambda runtime context)
    context = MockLambdaContext(
        function_name="S3FileProcessingSimulation",
        memory_limit_in_mb=128,
        timeout_seconds=15
    )

    print(f"[*] Function Name       : {context.function_name}")
    print(f"[*] Simulated Request ID: {context.aws_request_id}")
    print(f"[*] Memory Limit        : {context.memory_limit_in_mb} MB")
    print(f"[*] Invoking lambda_handler(event, context)...")
   

    # 3. Measure execution time and invoke handler
    start_time = time.perf_counter()
    response = lambda_handler(event, context)
    duration_ms = (time.perf_counter() - start_time) * 1000

 
    print(f"INVOCATION COMPLETED in {duration_ms:.2f} ms")
    print(f"[*] HTTP Status Code    : {response.get('statusCode')}")
    
    print("RESPONSE BODY:")
    try:
        body = json.loads(response.get("body", "{}"))
        print(json.dumps(body, indent=4))
    except Exception:
        print(response.get("body"))


    # 4. Verify generated output file
    output_file = os.path.join(base_dir, "output", "result.json")
    if os.path.exists(output_file):
        print(f"Output file successfully created at:\n   {output_file}")
    else:
        print(f"Warning: Output file was not found at {output_file}")


if __name__ == "__main__":
    main()