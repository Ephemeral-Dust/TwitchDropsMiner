#!/usr/bin/env python3
"""
Rust Drops Analyzer - Pull all Rust drops and show their API structure.
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RustDropsAnalyzer")


async def analyze_rust_drops():
    """Pull all Rust drops and show their complete API structure."""

    try:
        # Import after logging setup
        from twitch import Twitch
        from settings import Settings
        from constants import GQL_OPERATIONS
        import argparse

        logger.info("🎮 Initializing Rust Drops Analyzer...")

        # Create minimal settings
        args = argparse.Namespace()
        args._verbose = 1
        args._debug_ws = False
        args._debug_gql = False
        args.log = False
        args.tray = False
        args.dump = False

        settings = Settings(args)
        twitch = Twitch(settings)

        # Try to fetch campaigns directly
        logger.info("Fetching all campaigns...")
        try:
            campaigns_response = await twitch.gql_request(
                GQL_OPERATIONS["Campaigns"]
            )
            logger.info("✓ Successfully fetched campaigns")
        except Exception as e:
            logger.error(f"❌ Failed to fetch campaigns: {e}")
            return False

        # Initialize results structure
        results = {
            "timestamp": datetime.now().isoformat(),
            "rust_campaigns": [],
            "rust_drops": [],
            "all_games_seen": set(),
            "benefit_types_in_rust": set(),
            "raw_campaigns_data": campaigns_response,
        }

        # Analyze campaigns for Rust drops
        campaigns = (
            campaigns_response.get("data", {})
            .get("currentUser", {})
            .get("dropCampaigns", [])
        )
        logger.info(f"Found {len(campaigns)} total campaigns")

        rust_campaigns_count = 0
        rust_drops_count = 0

        for campaign in campaigns:
            campaign_name = campaign.get("name", "Unknown")
            game_data = campaign.get("game", {})
            game_name = (
                game_data.get("displayName", "Unknown")
                if game_data
                else "Unknown"
            )

            # Track all games we see
            results["all_games_seen"].add(game_name)

            # Check if this is a Rust campaign
            is_rust = (
                "rust" in game_name.lower() or "rust" in campaign_name.lower()
            )

            if is_rust:
                rust_campaigns_count += 1
                logger.info(
                    f"🎮 RUST CAMPAIGN: {campaign_name} (Game: {game_name})"
                )

                # Store the full campaign data
                campaign_info = {
                    "campaign_name": campaign_name,
                    "game_name": game_name,
                    "campaign_id": campaign.get("id", ""),
                    "status": campaign.get("status", "UNKNOWN"),
                    "drops": [],
                    "raw_campaign_data": campaign,
                }

                # Analyze each drop in this campaign
                for drop in campaign.get("timeBasedDrops", []):
                    rust_drops_count += 1
                    drop_name = drop.get("name", "Unknown Drop")
                    drop_id = drop.get("id", "")

                    logger.info(f"  📦 DROP: {drop_name}")

                    # Analyze benefits in detail
                    benefits = []
                    for benefit_edge in drop.get("benefitEdges", []):
                        benefit = benefit_edge.get("benefit", {})
                        if benefit:
                            benefit_type = benefit.get(
                                "distributionType", "UNKNOWN"
                            )
                            benefit_name = benefit.get("name", "Unknown")

                            results["benefit_types_in_rust"].add(benefit_type)

                            benefit_info = {
                                "name": benefit_name,
                                "type": benefit_type,
                                "id": benefit.get("id", ""),
                                "image_url": benefit.get("imageAssetURL", ""),
                                "raw_benefit_data": benefit,
                            }
                            benefits.append(benefit_info)

                            logger.info(
                                f"    🎁 BENEFIT: {benefit_name} (Type: {benefit_type})"
                            )

                            # Show extra details for emote types
                            if benefit_type == "EMOTE":
                                logger.info(f"      🎭 EMOTE DETECTED!")
                                logger.info(
                                    f"      Image: {benefit.get('imageAssetURL', 'No URL')}"
                                )

                    # Store drop info
                    drop_info = {
                        "drop_name": drop_name,
                        "drop_id": drop_id,
                        "starts_at": drop.get("startAt", ""),
                        "ends_at": drop.get("endAt", ""),
                        "required_minutes": drop.get(
                            "requiredMinutesWatched", 0
                        ),
                        "benefits": benefits,
                        "benefit_count": len(benefits),
                        "has_emote": any(
                            b["type"] == "EMOTE" for b in benefits
                        ),
                        "has_badge": any(
                            b["type"] == "BADGE" for b in benefits
                        ),
                        "raw_drop_data": drop,
                    }

                    campaign_info["drops"].append(drop_info)
                    results["rust_drops"].append(drop_info)

                    logger.info(
                        f"    ⏱️  Required: {drop.get('requiredMinutesWatched', 0)} minutes"
                    )
                    logger.info(f"    📊 Benefits: {len(benefits)} total")

                results["rust_campaigns"].append(campaign_info)

        # Convert sets to lists for JSON serialization
        results["all_games_seen"] = list(results["all_games_seen"])
        results["benefit_types_in_rust"] = list(
            results["benefit_types_in_rust"]
        )

        # Save complete results
        output_file = "rust_drops_complete_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info(f"\n📊 RUST DROPS ANALYSIS SUMMARY:")
        logger.info(f"  Total campaigns checked: {len(campaigns)}")
        logger.info(f"  Rust campaigns found: {rust_campaigns_count}")
        logger.info(f"  Rust drops found: {rust_drops_count}")
        logger.info(
            f"  Benefit types in Rust: {', '.join(sorted(results['benefit_types_in_rust']))}"
        )

        # Show emote drops specifically
        emote_drops = [
            drop for drop in results["rust_drops"] if drop["has_emote"]
        ]
        if emote_drops:
            logger.info(f"\n🎭 EMOTE DROPS IN RUST:")
            for i, drop in enumerate(emote_drops, 1):
                logger.info(f"  {i}. {drop['drop_name']}")
                emote_benefits = [
                    b for b in drop["benefits"] if b["type"] == "EMOTE"
                ]
                for emote in emote_benefits:
                    logger.info(f"     🎭 {emote['name']} (ID: {emote['id']})")
        else:
            logger.info(f"\n🎭 No emote drops found in Rust campaigns")

        # Show all games for context
        # logger.info(
        #     f"\n🎮 ALL GAMES WITH DROPS ({len(results['all_games_seen'])}):"
        # )
        # for game in sorted(results["all_games_seen"]):
        #     logger.info(f"  - {game}")

        logger.info(f"\n💾 Complete analysis saved to '{output_file}'")

        # Shutdown
        await twitch.shutdown()
        logger.info("✅ Rust drops analysis complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Error during analysis: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(analyze_rust_drops())
    sys.exit(0 if success else 1)
