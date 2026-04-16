#!/usr/bin/env python3
"""
Enhanced Rust Drops Analyzer - Get detailed drop data using CampaignDetails.
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
logger = logging.getLogger("RustDropsDetailed")


async def analyze_rust_drops_detailed():
    """Pull detailed Rust drop data using CampaignDetails queries."""

    try:
        # Import after logging setup
        from twitch import Twitch
        from settings import Settings
        from constants import GQL_OPERATIONS
        import argparse

        logger.info("🎮 Initializing Enhanced Rust Drops Analyzer...")

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

        # Fetch campaigns first
        logger.info("Fetching all campaigns...")
        campaigns_response = await twitch.gql_request(
            GQL_OPERATIONS["Campaigns"]
        )
        logger.info("✓ Successfully fetched campaigns")

        # Initialize results
        results = {
            "timestamp": datetime.now().isoformat(),
            "rust_campaigns": [],
            "detailed_rust_data": [],
            "all_rust_drops": [],
            "benefit_types_found": set(),
            "errors": [],
        }

        # Find Rust campaigns
        campaigns = (
            campaigns_response.get("data", {})
            .get("currentUser", {})
            .get("dropCampaigns", [])
        )
        rust_campaigns = []

        for campaign in campaigns:
            game_data = campaign.get("game", {})
            game_name = game_data.get("displayName", "") if game_data else ""

            if "rust" in game_name.lower():
                rust_campaigns.append(campaign)
                logger.info(
                    f"🎮 Found Rust campaign: {campaign.get('name', 'Unknown')}"
                )

        logger.info(
            f"Found {len(rust_campaigns)} Rust campaigns, getting detailed data..."
        )

        # Get detailed data for each Rust campaign
        for i, campaign in enumerate(rust_campaigns, 1):
            campaign_id = campaign.get("id", "")
            campaign_name = campaign.get("name", "Unknown")

            logger.info(
                f"[{i}/{len(rust_campaigns)}] Getting details for: {campaign_name}"
            )

            try:
                # Use CampaignDetails query to get full drop information
                details_response = await twitch.gql_request(
                    GQL_OPERATIONS["CampaignDetails"].with_variables(
                        {
                            "channelLogin": "",  # Empty as per the original code
                            "dropID": campaign_id,
                        }
                    )
                )

                campaign_details = (
                    details_response.get("data", {})
                    .get("user", {})
                    .get("dropCampaign", {})
                )

                if campaign_details:
                    logger.info(f"  ✓ Got detailed data for {campaign_name}")

                    # Store the detailed campaign
                    detailed_campaign = {
                        "campaign_name": campaign_name,
                        "campaign_id": campaign_id,
                        "status": campaign.get("status", "UNKNOWN"),
                        "starts_at": campaign.get("startAt", ""),
                        "ends_at": campaign.get("endAt", ""),
                        "details_url": campaign.get("detailsURL", ""),
                        "account_link_url": campaign.get("accountLinkURL", ""),
                        "drops": [],
                        "raw_details_data": campaign_details,
                    }

                    # Analyze time-based drops from detailed data
                    time_based_drops = campaign_details.get(
                        "timeBasedDrops", []
                    )
                    logger.info(
                        f"    📦 Found {len(time_based_drops)} drops in this campaign"
                    )

                    for drop in time_based_drops:
                        drop_name = drop.get("name", "Unknown Drop")
                        drop_id = drop.get("id", "")
                        required_minutes = drop.get(
                            "requiredMinutesWatched", 0
                        )

                        logger.info(
                            f"      🎁 DROP: {drop_name} ({required_minutes} min)"
                        )

                        # Analyze benefits
                        benefits = []
                        for benefit_edge in drop.get("benefitEdges", []):
                            benefit = benefit_edge.get("benefit", {})
                            if benefit:
                                benefit_type = benefit.get(
                                    "distributionType", "UNKNOWN"
                                )
                                benefit_name = benefit.get("name", "Unknown")

                                results["benefit_types_found"].add(
                                    benefit_type
                                )

                                benefit_info = {
                                    "name": benefit_name,
                                    "type": benefit_type,
                                    "id": benefit.get("id", ""),
                                    "image_url": benefit.get(
                                        "imageAssetURL", ""
                                    ),
                                    "raw_benefit": benefit,
                                }
                                benefits.append(benefit_info)

                                logger.info(
                                    f"        🎯 {benefit_name} ({benefit_type})"
                                )

                                # Highlight emotes
                                if benefit_type == "EMOTE":
                                    logger.info(
                                        f"        🎭 *** EMOTE FOUND! ***"
                                    )

                        # Store drop info
                        drop_info = {
                            "drop_name": drop_name,
                            "drop_id": drop_id,
                            "campaign_name": campaign_name,
                            "required_minutes": required_minutes,
                            "starts_at": drop.get("startAt", ""),
                            "ends_at": drop.get("endAt", ""),
                            "benefits": benefits,
                            "benefit_types": list(
                                set(b["type"] for b in benefits)
                            ),
                            "has_emote": any(
                                b["type"] == "EMOTE" for b in benefits
                            ),
                            "has_badge": any(
                                b["type"] == "BADGE" for b in benefits
                            ),
                            "raw_drop_data": drop,
                        }

                        detailed_campaign["drops"].append(drop_info)
                        results["all_rust_drops"].append(drop_info)

                    results["detailed_rust_data"].append(detailed_campaign)
                else:
                    logger.warning(
                        f"  ⚠️  No detailed data found for {campaign_name}"
                    )

            except Exception as e:
                error_msg = f"Failed to get details for {campaign_name}: {e}"
                logger.error(f"  ❌ {error_msg}")
                results["errors"].append(error_msg)

        # Convert sets to lists for JSON serialization
        results["benefit_types_found"] = list(results["benefit_types_found"])

        # Save complete results
        output_file = "rust_drops_detailed_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info(f"\n📊 DETAILED RUST DROPS ANALYSIS:")
        logger.info(f"  Rust campaigns analyzed: {len(rust_campaigns)}")
        logger.info(
            f"  Total Rust drops found: {len(results['all_rust_drops'])}"
        )
        logger.info(
            f"  Benefit types found: {', '.join(sorted(results['benefit_types_found']))}"
        )
        logger.info(f"  Errors encountered: {len(results['errors'])}")

        # Show emote drops
        emote_drops = [
            drop for drop in results["all_rust_drops"] if drop["has_emote"]
        ]
        if emote_drops:
            logger.info(f"\n🎭 EMOTE DROPS IN RUST ({len(emote_drops)}):")
            for drop in emote_drops:
                logger.info(
                    f"  📦 {drop['drop_name']} (Campaign: {drop['campaign_name']})"
                )
                emote_benefits = [
                    b for b in drop["benefits"] if b["type"] == "EMOTE"
                ]
                for emote in emote_benefits:
                    logger.info(f"    🎭 {emote['name']} (ID: {emote['id']})")
        else:
            logger.info(f"\n🎭 No emote drops found in current Rust campaigns")

        # Show all benefit types found
        if results["benefit_types_found"]:
            logger.info(f"\n🏷️  ALL BENEFIT TYPES IN RUST:")
            for benefit_type in sorted(results["benefit_types_found"]):
                count = sum(
                    1
                    for drop in results["all_rust_drops"]
                    for benefit in drop["benefits"]
                    if benefit["type"] == benefit_type
                )
                logger.info(f"  - {benefit_type}: {count} occurrences")

        logger.info(
            f"\n💾 Complete detailed analysis saved to '{output_file}'"
        )

        # Shutdown
        await twitch.shutdown()
        logger.info("✅ Detailed Rust drops analysis complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Error during analysis: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(analyze_rust_drops_detailed())
    sys.exit(0 if success else 1)
