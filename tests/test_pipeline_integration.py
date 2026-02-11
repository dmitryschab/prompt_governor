#!/usr/bin/env python3
"""Test script for Phase F2: Pipeline Integration.

This script verifies:
1. Pipeline imports work
2. ModularPipeline can be instantiated
3. Schema validation works
4. Metrics calculation works
5. Cost tracking works
"""

import sys
import os
from pathlib import Path

# Add paths for testing (simulating Docker environment)
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/prompt_optimization")


def test_pipeline_imports():
    """Test that all pipeline imports work."""
    print("=" * 60)
    print("TEST 1: Pipeline Imports")
    print("=" * 60)

    try:
        from pipelines.modular_pipeline import ModularPipeline

        print("✓ ModularPipeline imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ModularPipeline: {e}")
        return False

    try:
        from schemas.contract import Contract

        print("✓ Contract schema imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Contract schema: {e}")
        return False

    try:
        from utils.openrouter_client import estimate_cost

        print("✓ estimate_cost imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import estimate_cost: {e}")
        return False

    try:
        from utils.recall_metrics import calculate_recall_accuracy

        print("✓ calculate_recall_accuracy imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import calculate_recall_accuracy: {e}")
        return False

    return True


def test_pipeline_instantiation():
    """Test that ModularPipeline can be instantiated."""
    print("\n" + "=" * 60)
    print("TEST 2: Pipeline Instantiation")
    print("=" * 60)

    try:
        from pipelines.modular_pipeline import ModularPipeline

        # Create pipeline with default config
        pipeline = ModularPipeline(
            model_name="gpt-5-mini",
            reasoning_effort="low",
            enable_mandatory_fallback=True,
        )
        print(f"✓ ModularPipeline instantiated successfully")
        print(f"  - Model: {pipeline.model_name}")
        print(f"  - Reasoning effort: {pipeline.reasoning_effort}")
        print(f"  - Pipeline version: {pipeline.pipeline_version}")
        print(f"  - Modules: {list(pipeline.modules.keys())}")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate ModularPipeline: {e}")
        return False


def test_schema_validation():
    """Test that Contract schema validation works."""
    print("\n" + "=" * 60)
    print("TEST 3: Schema Validation")
    print("=" * 60)

    try:
        from schemas.contract import Contract

        # Sample contract data
        sample_data = {
            "GeneralInformation": {
                "TypeOfParticipation": "Treaty",
                "BusinessType": "Non-Prop Treaty",
            }
        }

        # Validate against schema
        contract = Contract.model_validate(sample_data)
        print("✓ Contract schema validation works")
        print(f"  - Contract structure: {contract.contract_structure}")
        return True
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
        return False


def test_metrics_calculation():
    """Test that recall metrics calculation works."""
    print("\n" + "=" * 60)
    print("TEST 4: Metrics Calculation")
    print("=" * 60)

    try:
        from utils.recall_metrics import calculate_recall_accuracy

        # Sample ground truth and output
        ground_truth = {
            "GeneralInformation": {
                "ContractName": "Test Contract",
                "BusinessType": "Non-Prop Treaty",
            }
        }

        model_output = {
            "GeneralInformation": {
                "ContractName": "Test Contract",
                "BusinessType": "Non-Prop Treaty",
            }
        }

        result = calculate_recall_accuracy(ground_truth, model_output)
        print("✓ Recall metrics calculation works")
        print(f"  - Recall: {result['recall']:.1f}%")
        print(f"  - Matched: {result['matched']}/{result['total_gt_fields']}")
        return True
    except Exception as e:
        print(f"✗ Metrics calculation failed: {e}")
        return False


def test_cost_estimation():
    """Test that cost estimation works."""
    print("\n" + "=" * 60)
    print("TEST 5: Cost Tracking")
    print("=" * 60)

    try:
        from utils.openrouter_client import OPENROUTER_PRICING

        print("✓ Cost pricing data available")
        print(f"  - Available models: {len(OPENROUTER_PRICING)}")

        # Check for common models
        models_to_check = [
            "openai/gpt-5-mini",
            "openai/gpt-4o",
        ]

        for model in models_to_check:
            if model in OPENROUTER_PRICING:
                pricing = OPENROUTER_PRICING[model]
                print(
                    f"  - {model}: ${pricing['prompt']}/${pricing['completion']} per 1M tokens"
                )

        return True
    except Exception as e:
        print(f"✗ Cost estimation failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("PHASE F2: Pipeline Integration Tests")
    print("=" * 60)
    print()

    results = []

    # Run all tests
    results.append(("Pipeline Imports", test_pipeline_imports()))
    results.append(("Pipeline Instantiation", test_pipeline_instantiation()))
    results.append(("Schema Validation", test_schema_validation()))
    results.append(("Metrics Calculation", test_metrics_calculation()))
    results.append(("Cost Tracking", test_cost_estimation()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All integration tests passed!")
        return 0
    else:
        print("\n  ⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
