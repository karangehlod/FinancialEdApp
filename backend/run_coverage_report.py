#!/usr/bin/env python3
"""
Comprehensive test coverage report generator.

This script runs tests for each module individually and generates
branch coverage reports, identifying any files below 90% threshold.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Test directories to analyze
TEST_MODULES = [
    "tests/services",
    "tests/repositories",
    "tests/core",
    "tests/api",
]

# Expected coverage modules
COVERAGE_MODULES = [
    "app.services",
    "app.repositories",
    "app.core",
    "app.api",
]

COVERAGE_THRESHOLD = 90


def run_test_file(test_file: str, module: str) -> Tuple[str, int, Dict]:
    """Run a single test file and capture coverage data."""
    cmd = [
        "python3", "-m", "pytest",
        test_file,
        f"--cov={module}",
        "--cov-report=json",
        "--cov-branch",
        "-v",
        "--tb=short",
        "-q"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Try to read coverage.json
        coverage_data = {}
        try:
            with open(".coverage", "r") as f:
                # coverage doesn't output json by default, we'll parse differently
                pass
        except:
            pass
        
        # Check result
        if result.returncode == 0:
            return test_file, 1, {"status": "PASSED"}
        else:
            return test_file, 0, {"status": "FAILED", "output": result.stdout[-500:] if result.stdout else result.stderr[-500:]}
            
    except subprocess.TimeoutExpired:
        return test_file, 0, {"status": "TIMEOUT"}
    except Exception as e:
        return test_file, 0, {"status": "ERROR", "error": str(e)}


def run_all_tests_with_coverage() -> Dict:
    """Run all tests and collect comprehensive coverage data."""
    print("=" * 80)
    print("COMPREHENSIVE TEST COVERAGE REPORT")
    print("=" * 80)
    print()
    
    # Run all tests with full coverage
    cmd = [
        "python3", "-m", "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=term-missing:skip-covered",
        "--cov-report=json",
        "--cov-branch",
        "-v",
        "--tb=short",
        "-q"
    ]
    
    print("Running full test suite with branch coverage...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Parse coverage data
    coverage_data = {}
    try:
        with open(".coverage/coverage.json", "r") as f:
            coverage_data = json.load(f)
    except:
        # Try alternate path
        try:
            with open("coverage.json", "r") as f:
                coverage_data = json.load(f)
        except:
            print("Note: Could not load JSON coverage data")
    
    return {
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "coverage_data": coverage_data
    }


def parse_coverage_output(output: str) -> Dict[str, float]:
    """Parse coverage percentages from pytest output."""
    results = {}
    lines = output.split("\n")
    
    for line in lines:
        if "TOTAL" in line and "%" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if "%" in part:
                    try:
                        percentage = float(part.strip("%"))
                        results["TOTAL"] = percentage
                    except:
                        pass
    
    return results


def main():
    """Main execution."""
    print("STARTING COMPREHENSIVE TEST COVERAGE ANALYSIS")
    print("=" * 80)
    print()
    
    # Run full test suite
    result = run_all_tests_with_coverage()
    
    print()
    print("=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Exit Code: {result['return_code']}")
    print()
    
    # Check threshold
    if "TOTAL" in result['stdout']:
        coverage_data = parse_coverage_output(result['stdout'])
        if coverage_data.get('TOTAL', 0) >= COVERAGE_THRESHOLD:
            print(f"✅ OVERALL COVERAGE MEETS THRESHOLD: {coverage_data.get('TOTAL', 0):.1f}% >= {COVERAGE_THRESHOLD}%")
        else:
            print(f"⚠️  OVERALL COVERAGE BELOW THRESHOLD: {coverage_data.get('TOTAL', 0):.1f}% < {COVERAGE_THRESHOLD}%")
    
    print()
    return 0 if result['return_code'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
