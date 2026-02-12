#!/usr/bin/env python3
"""
Data Migration Script for Prompt Governor

Migrates data from prompt_optimization project to prompt_governor:
- Prompt templates -> data/prompts/ (converted to PromptVersion format)
- Interpretations -> ground_truth/ (copied as-is)
- Sample documents -> documents/ (copied if any PDF/text files exist)

Usage:
    python scripts/migrate_data.py
"""

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Source and destination paths
SOURCE_BASE = Path.home() / "Documents/projects/prompt_optimization"
DEST_BASE = Path(__file__).parent.parent

SOURCE_PATHS = {
    "prompts": SOURCE_BASE / "prompt_templates",
    "docs": SOURCE_BASE / "docs",
    "interpretations": SOURCE_BASE / "interpretations",
}

DEST_PATHS = {
    "prompts": DEST_BASE / "data" / "prompts",
    "documents": DEST_BASE / "documents",
    "ground_truth": DEST_BASE / "ground_truth",
}


def ensure_directories() -> None:
    """Ensure all destination directories exist."""
    for path in DEST_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {path}")


def convert_prompt_template(source_data: dict, filename: str) -> dict:
    """Convert old prompt template format to new PromptVersion format.

    Maps:
    - Title -> name
    - Description -> description
    - Blocks[] -> blocks (title, body, comment)
    - Generates new UUID
    - Sets parent_id to None
    - Infers tags from content
    """
    # Generate UUID
    prompt_id = str(uuid4())

    # Extract name from Title or filename
    name = source_data.get("Title", filename.replace(".prompt_template", ""))

    # Extract description
    description = source_data.get("Description", "")

    # Convert blocks
    old_blocks = source_data.get("Blocks", [])
    blocks = []
    for block in old_blocks:
        new_block = {
            "title": block.get("Title", "Untitled Block"),
            "body": block.get("Body", ""),
            "comment": block.get("Comment", "") or None,
        }
        blocks.append(new_block)

    # Infer tags from content
    tags = []
    body_text = source_data.get("Body", "").lower()
    name_lower = name.lower()

    # Extract common tags based on content
    if "reinsurance" in name_lower or "reinsurance" in body_text:
        tags.append("reinsurance")
    if "contract" in name_lower or "contract" in body_text:
        tags.append("contract")
    if "extraction" in body_text:
        tags.append("extraction")
    if "production" in description.lower():
        tags.append("production")
    if "improved" in name_lower:
        tags.append("improved")

    return {
        "id": prompt_id,
        "name": name,
        "description": description or None,
        "blocks": blocks,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "parent_id": None,
        "tags": tags,
    }


def migrate_prompts() -> tuple[int, list[dict]]:
    """Migrate prompt templates from source to destination.

    Returns:
        Tuple of (count migrated, list of prompt metadata for index)
    """
    source_dir = SOURCE_PATHS["prompts"]
    dest_dir = DEST_PATHS["prompts"]

    if not source_dir.exists():
        logger.warning(f"Source directory not found: {source_dir}")
        return 0, []

    migrated_count = 0
    index_entries = []
    errors = []

    # Find all .prompt_template files
    template_files = list(source_dir.glob("*.prompt_template"))

    if not template_files:
        logger.warning(f"No .prompt_template files found in {source_dir}")
        return 0, []

    logger.info(f"Found {len(template_files)} prompt template(s) to migrate")

    for template_file in template_files:
        try:
            logger.info(f"Processing: {template_file.name}")

            # Read source file
            with open(template_file, "r", encoding="utf-8") as f:
                source_data = json.load(f)

            # Convert to new format
            prompt_version = convert_prompt_template(source_data, template_file.name)

            # Save to destination
            dest_file = dest_dir / f"{prompt_version['id']}.json"
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(prompt_version, f, indent=2, ensure_ascii=False)

            # Add to index entries
            index_entries.append(
                {
                    "id": prompt_version["id"],
                    "name": prompt_version["name"],
                    "description": prompt_version["description"],
                    "created_at": prompt_version["created_at"],
                    "parent_id": prompt_version["parent_id"],
                    "tags": prompt_version["tags"],
                }
            )

            migrated_count += 1
            logger.info(f"  ✓ Migrated to: {dest_file.name}")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {template_file.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to migrate {template_file.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)

    # Create index.json
    if index_entries:
        index_file = dest_dir / "index.json"
        index_data = {
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "count": len(index_entries),
            "prompts": index_entries,
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        logger.info(
            f"Created index.json with {len(index_entries)} entr{'y' if len(index_entries) == 1 else 'ies'}"
        )

    if errors:
        logger.warning(f"Encountered {len(errors)} error(s) during prompt migration")

    return migrated_count, index_entries


def migrate_ground_truth() -> int:
    """Migrate interpretation files (ground truth) from source to destination.

    Returns:
        Number of files migrated
    """
    source_dir = SOURCE_PATHS["interpretations"]
    dest_dir = DEST_PATHS["ground_truth"]

    if not source_dir.exists():
        logger.warning(f"Source directory not found: {source_dir}")
        return 0

    migrated_count = 0
    errors = []

    # Find all JSON files
    json_files = list(source_dir.glob("*.json"))

    if not json_files:
        logger.warning(f"No JSON files found in {source_dir}")
        return 0

    logger.info(f"Found {len(json_files)} ground truth file(s) to migrate")

    for json_file in json_files:
        try:
            logger.info(f"Processing: {json_file.name}")

            # Validate it's proper JSON
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Copy to destination
            dest_file = dest_dir / json_file.name
            shutil.copy2(json_file, dest_file)

            migrated_count += 1
            logger.info(f"  ✓ Copied to: {dest_file}")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {json_file.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to copy {json_file.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)

    if errors:
        logger.warning(
            f"Encountered {len(errors)} error(s) during ground truth migration"
        )

    return migrated_count


def migrate_documents() -> int:
    """Migrate PDF and text documents from source to destination.

    Returns:
        Number of files migrated
    """
    source_dir = SOURCE_PATHS["docs"]
    dest_dir = DEST_PATHS["documents"]

    if not source_dir.exists():
        logger.warning(f"Source directory not found: {source_dir}")
        return 0

    migrated_count = 0
    errors = []

    # Find all PDF and text files
    pdf_files = list(source_dir.glob("*.pdf"))
    txt_files = list(source_dir.glob("*.txt"))
    doc_files = pdf_files + txt_files

    if not doc_files:
        logger.info(
            f"No PDF or text files found in {source_dir} - skipping document migration"
        )
        return 0

    logger.info(
        f"Found {len(doc_files)} document(s) to migrate ({len(pdf_files)} PDF, {len(txt_files)} TXT)"
    )

    for doc_file in doc_files:
        try:
            logger.info(f"Processing: {doc_file.name}")

            # Copy to destination
            dest_file = dest_dir / doc_file.name
            shutil.copy2(doc_file, dest_file)

            migrated_count += 1
            logger.info(f"  ✓ Copied to: {dest_file}")

        except Exception as e:
            error_msg = f"Failed to copy {doc_file.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)

    if errors:
        logger.warning(f"Encountered {len(errors)} error(s) during document migration")

    return migrated_count


def generate_summary(
    prompts_migrated: int,
    ground_truth_migrated: int,
    documents_migrated: int,
    prompt_index: list[dict],
) -> dict:
    """Generate migration summary report."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_project": str(SOURCE_BASE),
        "destination_project": str(DEST_BASE),
        "migrated": {
            "prompts": {
                "count": prompts_migrated,
                "location": str(DEST_PATHS["prompts"]),
                "files": [p["name"] for p in prompt_index],
            },
            "ground_truth": {
                "count": ground_truth_migrated,
                "location": str(DEST_PATHS["ground_truth"]),
            },
            "documents": {
                "count": documents_migrated,
                "location": str(DEST_PATHS["documents"]),
            },
        },
        "total_files": prompts_migrated + ground_truth_migrated + documents_migrated,
    }


def main():
    """Main migration entry point."""
    logger.info("=" * 60)
    logger.info("Prompt Governor Data Migration")
    logger.info("=" * 60)
    logger.info(f"Source: {SOURCE_BASE}")
    logger.info(f"Destination: {DEST_BASE}")
    logger.info("")

    # Ensure directories exist
    logger.info("Step 1: Ensuring destination directories exist...")
    ensure_directories()
    logger.info("")

    # Migrate prompts
    logger.info("Step 2: Migrating prompt templates...")
    prompts_migrated, prompt_index = migrate_prompts()
    logger.info("")

    # Migrate ground truth
    logger.info("Step 3: Migrating ground truth files...")
    ground_truth_migrated = migrate_ground_truth()
    logger.info("")

    # Migrate documents
    logger.info("Step 4: Migrating sample documents...")
    documents_migrated = migrate_documents()
    logger.info("")

    # Generate summary
    summary = generate_summary(
        prompts_migrated,
        ground_truth_migrated,
        documents_migrated,
        prompt_index,
    )

    # Log summary
    logger.info("=" * 60)
    logger.info("Migration Complete")
    logger.info("=" * 60)
    logger.info(f"Prompts migrated: {prompts_migrated}")
    logger.info(f"Ground truth files migrated: {ground_truth_migrated}")
    logger.info(f"Documents migrated: {documents_migrated}")
    logger.info(f"Total files migrated: {summary['total_files']}")
    logger.info("")

    if prompt_index:
        logger.info("Migrated prompts:")
        for entry in prompt_index:
            logger.info(f"  - {entry['name']} (ID: {entry['id'][:8]}...)")
            if entry["tags"]:
                logger.info(f"    Tags: {', '.join(entry['tags'])}")

    # Save summary to file
    summary_file = DEST_BASE / "data" / "migration_summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("")
    logger.info(f"Summary saved to: {summary_file}")

    return summary


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result["total_files"] > 0 else 1)
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        sys.exit(1)
