#!/usr/bin/env python3
"""
Comprehensive test coverage analysis and refactoring guide.
Runs tests file by file and generates a detailed report.
"""

import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class FileResult:
    """Result for a single file's test execution."""
    filename: str
    module: str
    test_count: int
    passed: int
    failed: int
    coverage_percent: float
    branch_coverage: float
    status: str
    missing_lines: List[str]


def run_tests_for_file(test_file: str, app_module: str) -> Tuple[bool, str, float, float]:
    """Run tests for a single file and extract coverage data."""
    cmd = [
        "python3", "-m", "pytest",
        test_file,
        f"--cov={app_module}",
        "--cov-report=term-missing:skip-covered",
        "--cov-branch",
        "-v", "-q",
        "--tb=line"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        
        # Extract coverage percentage
        coverage = 0.0
        branch_coverage = 0.0
        
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "%" in part and i > 0:
                        try:
                            coverage = float(part.strip("%"))
                        except:
                            pass
                    if "TOTAL" in part:
                        # Look for branch coverage
                        pass
        
        success = result.returncode == 0
        return success, output, coverage, branch_coverage
        
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", 0.0, 0.0
    except Exception as e:
        return False, str(e), 0.0, 0.0


def main():
    """Main execution."""
    print("=" * 100)
    print("COMPREHENSIVE TEST COVERAGE AND BRANCH ANALYSIS")
    print("=" * 100)
    print()
    
    # Test each file individually
    test_files = [
        # Services
        ("tests/services/test_expense_service.py", "app.services.expense_service"),
        ("tests/services/test_expense_analytics_service.py", "app.services.expense_analytics_service"),
        ("tests/services/test_goal_service.py", "app.services.goal_service"),
        ("tests/services/test_budget_service.py", "app.services.budget_service"),
        ("tests/services/test_loan_service.py", "app.services.loan_service"),
        ("tests/services/test_auth_service.py", "app.services.auth_service"),
        # Repositories
        ("tests/repositories/test_expense_repository.py", "app.repositories.expense_repository"),
        ("tests/repositories/test_budget_repository.py", "app.repositories.budget_repository"),
        ("tests/repositories/test_user_repository.py", "app.repositories.user_repository"),
    ]
    
    results = []
    passed_files = 0
    failed_files = 0
    total_coverage = 0.0
    
    for test_file, app_module in test_files:
        test_path = Path(test_file)
        if not test_path.exists():
            print(f"⚠️  SKIP {test_file} - File not found")
            continue
        
        print(f"Running: {test_file}")
        success, output, coverage, branch = run_tests_for_file(test_file, app_module)
        
        if success:
            passed_files += 1
            status_icon = "✅"
        else:
            failed_files += 1
            status_icon = "❌"
        
        print(f"  {status_icon} Coverage: {coverage:.1f}%")
        if coverage >= 90:
            print(f"     ✅ Meets 90% threshold")
        else:
            print(f"     ⚠️  Below 90% threshold")
        print()
        
        results.append((test_file, coverage, success))
    
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Files Passed: {passed_files}")
    print(f"Files Failed: {failed_files}")
    print()
    
    # Summary of coverage thresholds
    print("Coverage Threshold Analysis (≥90% target):")
    print("-" * 50)
    
    for test_file, coverage, success in results:
        threshold_status = "✅" if coverage >= 90 else "⚠️"
        print(f"{threshold_status} {test_file.split('/')[-1]:40s} {coverage:6.1f}%")
    
    print()
    print("=" * 100)
    
    # Run full suite
    print()
    print("Running FULL test suite with comprehensive coverage...")
    print("-" * 100)
    
    cmd = [
        "python3", "-m", "pytest",
        "tests/services/",
        "tests/repositories/",
        "tests/core/",
        "--cov=app",
        "--cov-report=term-missing:skip-covered",
        "--cov-branch",
        "-v", "-q",
        "--tb=line"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # Print final summary
    lines = result.stdout.split("\n")
    for line in lines[-50:]:
        if line.strip():
            print(line)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
