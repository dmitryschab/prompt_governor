#!/usr/bin/env python3
"""
Load benchmark data from monolith benchmark results and create aggregated summaries.

This script:
1. Loads benchmark results from gpt-5-mini (minimal and low reasoning_effort)
2. Creates model configs for each reasoning effort level
3. Aggregates benchmark results with accuracy metrics
4. Outputs structured JSON for frontend visualization
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
BENCHMARK_BASE_PATH = Path(
    "/Users/dmitrijssabelniks/Documents/projects/prompt_optimization/monolith_benchmark_results/gpt-5-mini"
)
OUTPUT_CONFIGS_PATH = Path(
    "/Users/dmitrijssabelniks/Documents/projects/prompt_governor/data/configs"
)
OUTPUT_RUNS_PATH = Path(
    "/Users/dmitrijssabelniks/Documents/projects/prompt_governor/data/runs"
)

REASONING_EFFORTS = ["minimal", "low"]


def load_json_file(file_path: Path) -> dict[str, Any] | None:
    """Load a JSON file with error handling."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None


def save_json_file(file_path: Path, data: dict[str, Any]) -> bool:
    """Save data to a JSON file with error handling."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False


def update_index_json(index_path: Path, item_id: str, item_name: str) -> bool:
    """Update an index.json file with a new item."""
    try:
        index_data = {"items": [], "version": 1}

        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)

        # Check if item already exists
        existing_item = next(
            (item for item in index_data.get("items", []) if item.get("id") == item_id),
            None,
        )

        if existing_item:
            existing_item["name"] = item_name
            existing_item["updated_at"] = datetime.now().isoformat()
        else:
            index_data["items"].append(
                {
                    "id": item_id,
                    "name": item_name,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            )

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated index: {index_path}")
        return True
    except Exception as e:
        logger.error(f"Error updating index {index_path}: {e}")
        return False


def load_benchmark_results(reasoning_effort: str) -> dict[str, Any] | None:
    """Load benchmark summary for a specific reasoning effort."""
    summary_path = BENCHMARK_BASE_PATH / reasoning_effort / "benchmark_summary.json"
    logger.info(f"Loading benchmark summary: {summary_path}")

    data = load_json_file(summary_path)
    if data:
        logger.info(
            f"Loaded {data.get('documents', 0)} documents for {reasoning_effort}"
        )
    return data


def load_document_result(
    reasoning_effort: str, document_name: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load both result and metadata for a specific document."""
    base_path = BENCHMARK_BASE_PATH / reasoning_effort
    result_file = base_path / f"{document_name}.json"
    meta_file = base_path / f"{document_name}.meta.json"

    result_data = load_json_file(result_file)
    meta_data = load_json_file(meta_file)

    return result_data, meta_data


def create_model_config(
    reasoning_effort: str, benchmark_data: dict[str, Any]
) -> dict[str, Any]:
    """Create a model config for a specific reasoning effort."""
    config = {
        "id": f"gpt-5-mini-{reasoning_effort}",
        "name": f"GPT-5-mini ({reasoning_effort})",
        "model": "gpt-5-mini",
        "reasoning_effort": reasoning_effort,
        "temperature": 1.0,
        "provider": "openai",
        "description": f"GPT-5-mini with reasoning_effort='{reasoning_effort}' for contract extraction",
        "template": benchmark_data.get("template", ""),
        "mode": benchmark_data.get("mode", "monolith"),
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0",
    }

    # Extract request config details from first inference if available
    inference = benchmark_data.get("inference", [])
    if inference:
        first_doc = inference[0].get("document", "")
        _, meta_data = load_document_result(reasoning_effort, first_doc)
        if meta_data and "request_config" in meta_data:
            req_config = meta_data["request_config"]
            config["temperature"] = req_config.get("temperature", 1.0)
            config["contract_schema_hash"] = req_config.get(
                "contract_schema_sha256", ""
            )
            config["response_format_hash"] = req_config.get(
                "response_format_sha256", ""
            )

    return config


def calculate_aggregated_metrics(benchmark_data: dict[str, Any]) -> dict[str, Any]:
    """Calculate aggregated metrics from benchmark data."""
    inference = benchmark_data.get("inference", [])
    prf1_results = benchmark_data.get("prf1_results", [])

    if not inference:
        return {}

    # Calculate cost and latency summaries
    total_cost = sum(doc.get("cost_usd", 0) for doc in inference)
    total_latency = sum(doc.get("latency_s", 0) for doc in inference)
    total_prompt_tokens = sum(doc.get("prompt_tokens", 0) for doc in inference)
    total_completion_tokens = sum(doc.get("completion_tokens", 0) for doc in inference)
    total_tokens = sum(doc.get("total_tokens", 0) for doc in inference)

    successful_docs = [doc for doc in inference if doc.get("success", False)]
    cache_hits = [doc for doc in inference if doc.get("cache_hit", False)]

    # Calculate per-document metrics
    document_metrics = []
    for doc in inference:
        doc_name = doc.get("document", "")

        # Find matching PRF1 results
        prf1 = next((p for p in prf1_results if p.get("document") == doc_name), {})

        document_metrics.append(
            {
                "document_name": doc_name,
                "success": doc.get("success", False),
                "cache_hit": doc.get("cache_hit", False),
                "latency_s": round(doc.get("latency_s", 0), 2),
                "cost_usd": round(doc.get("cost_usd", 0), 6),
                "prompt_tokens": doc.get("prompt_tokens", 0),
                "completion_tokens": doc.get("completion_tokens", 0),
                "total_tokens": doc.get("total_tokens", 0),
                "accuracy": {
                    "structure_f1": round(prf1.get("structure_f1", 0), 3)
                    if prf1
                    else None,
                    "value_f1": round(prf1.get("value_f1", 0), 3) if prf1 else None,
                    "list_f1": round(prf1.get("list_f1", 0), 3) if prf1 else None,
                    "weighted_f1": round(prf1.get("weighted_f1", 0), 3)
                    if prf1
                    else None,
                },
            }
        )

    # Calculate field-level accuracy averages
    if prf1_results:
        avg_structure_f1 = sum(p.get("structure_f1", 0) for p in prf1_results) / len(
            prf1_results
        )
        avg_value_f1 = sum(p.get("value_f1", 0) for p in prf1_results) / len(
            prf1_results
        )
        avg_list_f1 = sum(p.get("list_f1", 0) for p in prf1_results) / len(prf1_results)
        avg_weighted_f1 = sum(p.get("weighted_f1", 0) for p in prf1_results) / len(
            prf1_results
        )
    else:
        avg_structure_f1 = avg_value_f1 = avg_list_f1 = avg_weighted_f1 = 0

    return {
        "overall": {
            "field_accuracy": round(benchmark_data.get("field_accuracy", 0), 2),
            "avg_structure_f1": round(avg_structure_f1, 3),
            "avg_value_f1": round(avg_value_f1, 3),
            "avg_list_f1": round(avg_list_f1, 3),
            "avg_weighted_f1": round(avg_weighted_f1, 3),
            "total_documents": len(inference),
            "successful_documents": len(successful_docs),
            "success_rate": round(len(successful_docs) / len(inference) * 100, 1)
            if inference
            else 0,
            "cache_hits": len(cache_hits),
            "cache_hit_rate": round(len(cache_hits) / len(inference) * 100, 1)
            if inference
            else 0,
        },
        "cost_summary": {
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_document": round(total_cost / len(inference), 6)
            if inference
            else 0,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "avg_tokens_per_document": round(total_tokens / len(inference), 0)
            if inference
            else 0,
        },
        "latency_summary": {
            "total_latency_s": round(total_latency, 2),
            "avg_latency_s": round(total_latency / len(inference), 2)
            if inference
            else 0,
            "min_latency_s": round(min(doc.get("latency_s", 0) for doc in inference), 2)
            if inference
            else 0,
            "max_latency_s": round(max(doc.get("latency_s", 0) for doc in inference), 2)
            if inference
            else 0,
        },
        "documents": document_metrics,
    }


def create_benchmark_summary() -> dict[str, Any]:
    """Create the aggregated benchmark summary."""
    summary = {
        "id": "benchmark-summary-gpt5-mini",
        "name": "GPT-5-mini Benchmark Summary",
        "description": "Aggregated benchmark results for GPT-5-mini with different reasoning efforts",
        "created_at": datetime.now().isoformat(),
        "model": "gpt-5-mini",
        "reasoning_efforts": {},
    }

    all_documents = set()

    for effort in REASONING_EFFORTS:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing reasoning effort: {effort}")
        logger.info(f"{'=' * 60}")

        benchmark_data = load_benchmark_results(effort)

        if not benchmark_data:
            logger.warning(f"No benchmark data found for {effort}")
            continue

        # Create and save model config
        config = create_model_config(effort, benchmark_data)
        config_path = OUTPUT_CONFIGS_PATH / f"{config['id']}.json"

        if save_json_file(config_path, config):
            update_index_json(
                OUTPUT_CONFIGS_PATH / "index.json", config["id"], config["name"]
            )

        # Calculate aggregated metrics
        metrics = calculate_aggregated_metrics(benchmark_data)

        # Collect document names
        for doc in benchmark_data.get("inference", []):
            all_documents.add(doc.get("document", ""))

        summary["reasoning_efforts"][effort] = {
            "config_id": config["id"],
            "config_name": config["name"],
            "template": benchmark_data.get("template", ""),
            "mode": benchmark_data.get("mode", "monolith"),
            "metrics": metrics,
        }

        logger.info(
            f"Processed {metrics['overall']['total_documents']} documents for {effort}"
        )
        logger.info(f"Field accuracy: {metrics['overall']['field_accuracy']}%")
        logger.info(f"Avg weighted F1: {metrics['overall']['avg_weighted_f1']}")
        logger.info(f"Total cost: ${metrics['cost_summary']['total_cost_usd']}")
        logger.info(f"Avg latency: {metrics['latency_summary']['avg_latency_s']}s")

    summary["document_count"] = len(all_documents)
    summary["document_names"] = sorted(list(all_documents))

    # Create comparison metrics
    if len(summary["reasoning_efforts"]) >= 2:
        summary["comparison"] = create_comparison(summary["reasoning_efforts"])

    return summary


def create_comparison(reasoning_efforts: dict[str, Any]) -> dict[str, Any]:
    """Create comparison metrics between reasoning efforts."""
    comparison = {"accuracy": {}, "cost": {}, "latency": {}, "recommendations": []}

    efforts = list(reasoning_efforts.keys())

    if len(efforts) >= 2:
        # Compare minimal vs low
        minimal = reasoning_efforts.get("minimal", {}).get("metrics", {})
        low = reasoning_efforts.get("low", {}).get("metrics", {})

        if minimal and low:
            # Accuracy comparison
            min_accuracy = minimal["overall"].get("field_accuracy", 0)
            low_accuracy = low["overall"].get("field_accuracy", 0)
            accuracy_diff = low_accuracy - min_accuracy

            comparison["accuracy"] = {
                "minimal": min_accuracy,
                "low": low_accuracy,
                "difference": round(accuracy_diff, 2),
                "improvement_pct": round((accuracy_diff / min_accuracy * 100), 1)
                if min_accuracy > 0
                else 0,
                "winner": "low"
                if low_accuracy > min_accuracy
                else "minimal"
                if min_accuracy > low_accuracy
                else "tie",
            }

            # Cost comparison
            min_cost = minimal["cost_summary"].get("total_cost_usd", 0)
            low_cost = low["cost_summary"].get("total_cost_usd", 0)
            cost_diff = low_cost - min_cost

            comparison["cost"] = {
                "minimal": min_cost,
                "low": low_cost,
                "difference": round(cost_diff, 4),
                "increase_pct": round((cost_diff / min_cost * 100), 1)
                if min_cost > 0
                else 0,
                "cost_per_accuracy_point": {
                    "minimal": round(min_cost / min_accuracy, 4)
                    if min_accuracy > 0
                    else 0,
                    "low": round(low_cost / low_accuracy, 4) if low_accuracy > 0 else 0,
                },
            }

            # Latency comparison
            min_latency = minimal["latency_summary"].get("avg_latency_s", 0)
            low_latency = low["latency_summary"].get("avg_latency_s", 0)
            latency_diff = low_latency - min_latency

            comparison["latency"] = {
                "minimal": min_latency,
                "low": low_latency,
                "difference": round(latency_diff, 2),
                "increase_pct": round((latency_diff / min_latency * 100), 1)
                if min_latency > 0
                else 0,
            }

            # Generate recommendations
            recommendations = []

            if accuracy_diff > 5:
                recommendations.append(
                    {
                        "type": "accuracy",
                        "priority": "high",
                        "message": f"Low reasoning effort shows {abs(accuracy_diff):.1f}% better accuracy",
                    }
                )
            elif accuracy_diff < -5:
                recommendations.append(
                    {
                        "type": "accuracy",
                        "priority": "medium",
                        "message": f"Minimal reasoning effort shows {abs(accuracy_diff):.1f}% better accuracy with lower cost",
                    }
                )

            cost_efficiency_min = min_accuracy / min_cost if min_cost > 0 else 0
            cost_efficiency_low = low_accuracy / low_cost if low_cost > 0 else 0

            if cost_efficiency_min > cost_efficiency_low * 1.2:
                recommendations.append(
                    {
                        "type": "cost_efficiency",
                        "priority": "high",
                        "message": "Minimal reasoning effort is significantly more cost-efficient",
                    }
                )
            elif cost_efficiency_low > cost_efficiency_min * 1.2:
                recommendations.append(
                    {
                        "type": "cost_efficiency",
                        "priority": "medium",
                        "message": "Low reasoning effort offers better accuracy per dollar spent",
                    }
                )

            if latency_diff > 10:
                recommendations.append(
                    {
                        "type": "latency",
                        "priority": "medium",
                        "message": f"Low reasoning effort takes {abs(latency_diff):.1f}s longer on average",
                    }
                )

            comparison["recommendations"] = recommendations

    return comparison


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Loading Benchmark Data")
    logger.info("=" * 60)
    logger.info(f"Source: {BENCHMARK_BASE_PATH}")
    logger.info(f"Output configs: {OUTPUT_CONFIGS_PATH}")
    logger.info(f"Output runs: {OUTPUT_RUNS_PATH}")

    # Verify source path exists
    if not BENCHMARK_BASE_PATH.exists():
        logger.error(f"Benchmark base path does not exist: {BENCHMARK_BASE_PATH}")
        sys.exit(1)

    # Create output directories if needed
    OUTPUT_CONFIGS_PATH.mkdir(parents=True, exist_ok=True)
    OUTPUT_RUNS_PATH.mkdir(parents=True, exist_ok=True)

    # Create benchmark summary
    summary = create_benchmark_summary()

    # Save benchmark summary
    summary_path = OUTPUT_RUNS_PATH / "benchmark_summary.json"
    if save_json_file(summary_path, summary):
        update_index_json(
            OUTPUT_RUNS_PATH / "index.json", summary["id"], summary["name"]
        )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Total unique documents: {summary['document_count']}")
    logger.info(f"Reasoning efforts processed: {len(summary['reasoning_efforts'])}")

    for effort, data in summary["reasoning_efforts"].items():
        metrics = data["metrics"]
        logger.info(f"\n{effort.upper()}:")
        logger.info(f"  - Documents: {metrics['overall']['total_documents']}")
        logger.info(f"  - Field accuracy: {metrics['overall']['field_accuracy']}%")
        logger.info(f"  - Weighted F1: {metrics['overall']['avg_weighted_f1']}")
        logger.info(f"  - Total cost: ${metrics['cost_summary']['total_cost_usd']}")
        logger.info(f"  - Avg latency: {metrics['latency_summary']['avg_latency_s']}s")

    if "comparison" in summary:
        comp = summary["comparison"]
        logger.info(f"\nCOMPARISON:")
        logger.info(
            f"  - Accuracy difference: {comp['accuracy'].get('difference', 0):.2f}%"
        )
        logger.info(f"  - Cost increase: {comp['cost'].get('increase_pct', 0):.1f}%")
        logger.info(
            f"  - Latency increase: {comp['latency'].get('increase_pct', 0):.1f}%"
        )

    logger.info("\n" + "=" * 60)
    logger.info("Done!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
