#!/usr/bin/env python3
"""
Simple emote drop checker - reads existing session data.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EmoteDropChecker")


def analyze_existing_data():
    """Analyze existing drop data from the miner's cache/logs."""

    logger.info("🔍 Checking for existing drop data...")

    # Check for existing inventory/drop files
    cache_dir = Path("cache")
    if cache_dir.exists():
        logger.info(f"Found cache directory: {cache_dir}")
        for file in cache_dir.glob("*.json"):
            logger.info(f"  Cache file: {file.name}")

    # Look for settings/state files that might contain drop info
    if Path("settings.json").exists():
        logger.info("Found settings.json")

    # Check if there are any debug files from previous runs
    debug_files = list(Path(".").glob("debug_*.js"))
    if debug_files:
        logger.info(f"Found {len(debug_files)} debug files")

    return True


def check_benefit_types_in_code():
    """Check what benefit types are already handled in the code."""

    logger.info("📋 Checking existing benefit types in code...")

    try:
        # Read the inventory.py file to see current benefit types
        with open("inventory.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Look for BenefitType enum
        if "class BenefitType" in content:
            logger.info("Found BenefitType enum in inventory.py")

            # Extract the enum values
            import re

            enum_match = re.search(
                r"class BenefitType\(Enum\):(.*?)(?=\n\n|\nclass|\Z)",
                content,
                re.DOTALL,
            )
            if enum_match:
                enum_content = enum_match.group(1)
                benefit_types = re.findall(
                    r'(\w+)\s*=\s*["\'](\w+)["\']', enum_content
                )

                logger.info("Current benefit types:")
                for name, value in benefit_types:
                    logger.info(f"  {name} = {value}")

                # Check if EMOTE is already handled
                emote_types = [
                    bt
                    for bt in benefit_types
                    if "EMOTE" in bt[0] or "EMOTE" in bt[1]
                ]
                if emote_types:
                    logger.info(
                        f"✅ EMOTE type already defined: {emote_types}"
                    )
                else:
                    logger.info(
                        "⚠️  No EMOTE type found in current definitions"
                    )

        return True
    except Exception as e:
        logger.error(f"Error reading inventory.py: {e}")
        return False


def create_manual_test_data():
    """Create sample test data to simulate emote drop structure."""

    logger.info("🧪 Creating sample emote drop test data...")

    # Based on typical Twitch drop structure, create what an emote drop might look like
    sample_emote_drop = {
        "id": "test_emote_drop_001",
        "name": "Special Twitch Emote Drop",
        "benefitEdges": [
            {
                "benefit": {
                    "id": "emote_benefit_123",
                    "name": "PogChamp Emote",
                    "distributionType": "EMOTE",
                    "imageAssetURL": "https://static-cdn.jtvnw.net/emoticons/v2/305954156/default/dark/1.0",
                }
            }
        ],
        "startAt": "2025-12-01T00:00:00Z",
        "endAt": "2025-12-31T23:59:59Z",
        "preconditionDrops": [],
        "self": {"dropInstanceID": "instance_123", "isClaimed": False},
    }

    sample_campaign = {
        "id": "test_campaign_emote",
        "name": "Emote Drop Test Campaign",
        "game": {"displayName": "Test Game"},
        "timeBasedDrops": [sample_emote_drop],
    }

    test_data = {
        "timestamp": datetime.now().isoformat(),
        "description": "Sample emote drop structure for testing",
        "sample_emote_drop": sample_emote_drop,
        "sample_campaign": sample_campaign,
        "analysis": {
            "emote_benefit_structure": "EMOTE type in distributionType field",
            "potential_issues": [
                "Need to verify EMOTE enum exists in BenefitType",
                "Check if emote drops require special handling vs regular drops",
                "Verify image URLs and claiming process",
            ],
        },
    }

    # Save test data
    with open("emote_drop_test_structure.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "💾 Sample emote drop structure saved to 'emote_drop_test_structure.json'"
    )

    return test_data


def main():
    """Main function to run emote drop analysis."""

    logger.info("🎭 Emote Drop Analysis Tool")
    logger.info("=" * 50)

    # Check existing data
    analyze_existing_data()

    # Check current code for benefit types
    check_benefit_types_in_code()

    # Create test structure
    create_manual_test_data()

    logger.info("\n📊 RECOMMENDATIONS:")
    logger.info("1. Check if BenefitType.EMOTE is properly defined")
    logger.info("2. Verify emote drops are handled in drop processing logic")
    logger.info("3. Test with actual emote drop campaigns when available")
    logger.info(
        "4. Run the main miner and monitor logs for EMOTE benefit types"
    )

    logger.info("\n🔧 To get live data:")
    logger.info("1. Run: python main.py --log")
    logger.info("2. Let it run for a while to collect campaign data")
    logger.info(
        "3. Check log.txt for any mentions of 'EMOTE' or unknown benefit types"
    )
    logger.info("4. Look in cache/ directory for saved campaign data")

    logger.info("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
