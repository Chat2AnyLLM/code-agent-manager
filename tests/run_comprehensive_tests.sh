#!/bin/bash

# Script to run all Python test files individually and report results
echo "Starting comprehensive test execution..."
echo "======================================"

# Find all test files and store them in an array
TEST_FILES=($(find . -type f -name "*test*.py" | grep -v .venv | sort))

# Counter for tracking
TOTAL_TESTS=${#TEST_FILES[@]}
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
FAILED_LIST=()

echo "Found $TOTAL_TESTS test files to execute."
echo ""

# Loop through each test file
for i in "${!TEST_FILES[@]}"; do
    test_file="${TEST_FILES[$i]}"
    echo "[$((i+1))/$TOTAL_TESTS] Running: $test_file"

    # Execute the test
    result=$(python -m pytest "$test_file" -v 2>&1)
    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        # Check if the test passed by looking for "passed" in output
        if echo "$result" | grep -q "failed"; then
            echo "  ❌ FAILED - has failed tests"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            FAILED_LIST+=("$test_file")
        elif echo "$result" | grep -q "passed"; then
            echo "  ✅ PASSED"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "  ⚠️  SKIPPED or NO TESTS"
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        fi
    else
        echo "  ❌ FAILED - execution error"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_LIST+=("$test_file")
    fi

    # Show summary of this test run if it has results
    if echo "$result" | grep -q "passed\|failed\|skipped"; then
        passed_count=$(echo "$result" | grep -o "[0-9]\+ passed" | head -1 | grep -o "[0-9]\+")
        failed_count=$(echo "$result" | grep -o "[0-9]\+ failed" | head -1 | grep -o "[0-9]\+")
        skipped_count=$(echo "$result" | grep -o "[0-9]\+ skipped" | head -1 | grep -o "[0-9]\+")

        [[ -z "$passed_count" ]] && passed_count=0
        [[ -z "$failed_count" ]] && failed_count=0
        [[ -z "$skipped_count" ]] && skipped_count=0

        echo "      Summary: $passed_count passed, $failed_count failed, $skipped_count skipped"
    fi
    echo ""
done

# Final summary
echo "======================================"
echo "COMPREHENSIVE TEST EXECUTION COMPLETE"
echo "======================================"
echo "Total tests executed: $TOTAL_TESTS"
echo "✅ Passed: $PASSED_TESTS"
echo "❌ Failed: $FAILED_TESTS"
echo "⚠️  Skipped/No tests: $SKIPPED_TESTS"
echo ""

if [ $FAILED_TESTS -gt 0 ]; then
    echo "Failed tests:"
    for failed_test in "${FAILED_LIST[@]}"; do
        echo "  - $failed_test"
    done
    echo ""
    exit 1
else
    echo "🎉 All tests passed!"
    exit 0
fi