#!/usr/bin/env python3
"""
Rust 12th Anniversary Deep Dive Analyzer
Specifically investigate the Rust 12th Anniversary campaign and its emote drops.
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RustAnniversaryAnalyzer")


async def analyze_rust_anniversary():
    """Deep dive into the Rust 12th Anniversary campaign."""

    try:
        # Import after logging setup
        from twitch import Twitch
        from settings import Settings
        from constants import GQL_OPERATIONS
        import argparse

        logger.info("🎂 Initializing Rust 12th Anniversary Deep Dive...")

        # Create minimal settings
        args = argparse.Namespace()
        args._verbose = 1
        args._debug_ws = False
        args._debug_gql = True  # Enable GQL debugging to see raw queries
        args.log = False
        args.tray = False
        args.dump = False

        settings = Settings(args)
        twitch = Twitch(settings)

        results = {
            "timestamp": datetime.now().isoformat(),
            "target_campaign": "Rust 12th Anniversary",
            "queries_attempted": [],
            "raw_responses": {},
            "errors": [],
        }

        # First, find the campaign ID for "Rust 12th Anniversary"
        logger.info("Step 1: Finding Rust 12th Anniversary campaign...")
        campaigns_response = await twitch.gql_request(
            GQL_OPERATIONS["Campaigns"]
        )

        results["queries_attempted"].append("Campaigns")
        results["raw_responses"]["campaigns"] = campaigns_response

        rust_anniversary_campaign = None
        campaigns = (
            campaigns_response.get("data", {})
            .get("currentUser", {})
            .get("dropCampaigns", [])
        )

        for campaign in campaigns:
            campaign_name = campaign.get("name", "")
            if "Rust 12th Anniversary" in campaign_name:
                rust_anniversary_campaign = campaign
                logger.info(f"✓ Found target campaign: {campaign_name}")
                logger.info(f"  Campaign ID: {campaign.get('id', 'Unknown')}")
                logger.info(f"  Status: {campaign.get('status', 'Unknown')}")
                logger.info(f"  Start: {campaign.get('startAt', 'Unknown')}")
                logger.info(f"  End: {campaign.get('endAt', 'Unknown')}")
                break

        if not rust_anniversary_campaign:
            logger.error("❌ Could not find 'Rust 12th Anniversary' campaign")
            return False

        campaign_id = rust_anniversary_campaign.get("id", "")
        logger.info(f"Target Campaign ID: {campaign_id}")

        # Step 2: Try different queries to get drop details
        queries_to_try = [
            ("CampaignDetails", {"channelLogin": "", "dropID": campaign_id}),
            ("Inventory", {"fetchRewardCampaigns": False}),
            (
                "CurrentDrop",
                {"channelID": "165528919", "channelLogin": ""},  # Your user ID
            ),
        ]

        for query_name, variables in queries_to_try:
            logger.info(
                f"\nStep 2.{len(results['queries_attempted'])+1}: Trying {query_name} query..."
            )

            try:
                if variables:
                    response = await twitch.gql_request(
                        GQL_OPERATIONS[query_name].with_variables(variables)
                    )
                else:
                    response = await twitch.gql_request(
                        GQL_OPERATIONS[query_name]
                    )

                results["queries_attempted"].append(query_name)
                results["raw_responses"][query_name.lower()] = response

                logger.info(f"✓ {query_name} query successful")

                # Check for drop data in this response
                data = response.get("data", {})
                logger.debug(
                    f"{query_name} response keys: {list(data.keys())}"
                )

                # Look for drops in various parts of the response
                drops_found = []

                # Check different possible locations for drops
                possible_paths = [
                    ["user", "dropCampaign", "timeBasedDrops"],
                    ["currentUser", "dropCampaignsInProgress"],
                    ["currentUser", "dropCampaigns"],
                    ["channel", "viewerDropCampaigns"],
                ]

                for path in possible_paths:
                    current = data
                    try:
                        for key in path:
                            current = (
                                current.get(key, {})
                                if isinstance(current, dict)
                                else current
                            )

                        if current and isinstance(current, list):
                            logger.info(
                                f"  Found data at path {' -> '.join(path)}: {len(current)} items"
                            )

                            # If this is campaigns, look for our target
                            for item in current:
                                if isinstance(item, dict):
                                    item_name = item.get("name", "")
                                    if (
                                        "12th Anniversary" in item_name
                                        or item.get("id") == campaign_id
                                    ):
                                        logger.info(
                                            f"    Found target campaign in {query_name}!"
                                        )

                                        # Check for timeBasedDrops in this item
                                        time_drops = item.get(
                                            "timeBasedDrops", []
                                        )
                                        if time_drops:
                                            logger.info(
                                                f"    ✓ Found {len(time_drops)} drops in this campaign!"
                                            )
                                            drops_found.extend(time_drops)
                                        else:
                                            logger.info(
                                                f"    No timeBasedDrops in this item"
                                            )
                                            logger.debug(
                                                f"    Item keys: {list(item.keys())}"
                                            )
                    except Exception as e:
                        logger.debug(f"  Error checking path {path}: {e}")

                if drops_found:
                    logger.info(
                        f"🎁 Found {len(drops_found)} drops from {query_name}!"
                    )

                    for i, drop in enumerate(drops_found):
                        drop_name = drop.get("name", f"Drop {i+1}")
                        logger.info(f"\n  📦 DROP: {drop_name}")
                        logger.info(f"    ID: {drop.get('id', 'Unknown')}")
                        logger.info(
                            f"    Required minutes: {drop.get('requiredMinutesWatched', 0)}"
                        )

                        # Analyze benefits
                        benefits = drop.get("benefitEdges", [])
                        logger.info(f"    Benefits: {len(benefits)}")

                        for j, benefit_edge in enumerate(benefits):
                            benefit = benefit_edge.get("benefit", {})
                            if benefit:
                                b_name = benefit.get("name", f"Benefit {j+1}")
                                b_type = benefit.get(
                                    "distributionType", "UNKNOWN"
                                )
                                b_id = benefit.get("id", "Unknown")

                                logger.info(f"      🎁 {b_name}")
                                logger.info(f"        Type: {b_type}")
                                logger.info(f"        ID: {b_id}")
                                logger.info(
                                    f"        Image: {benefit.get('imageAssetURL', 'No image')}"
                                )

                                if b_type == "EMOTE":
                                    logger.info(
                                        f"        🎭 *** EMOTE FOUND! ***"
                                    )
                                    logger.info(
                                        f"        Full benefit data: {json.dumps(benefit, indent=10)}"
                                    )

                else:
                    logger.info(f"  No drops found in {query_name} response")

            except Exception as e:
                error_msg = f"Error with {query_name} query: {e}"
                logger.error(f"❌ {error_msg}")
                results["errors"].append(error_msg)

        # Step 3: Save all raw data for manual inspection
        output_file = "rust_anniversary_deep_dive.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(
            f"\n💾 All raw data saved to '{output_file}' for manual inspection"
        )
        logger.info(
            f"📋 Queries attempted: {', '.join(results['queries_attempted'])}"
        )
        logger.info(f"❌ Errors: {len(results['errors'])}")

        # Shutdown
        await twitch.shutdown()
        logger.info("✅ Deep dive analysis complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(analyze_rust_anniversary())
    sys.exit(0 if success else 1)
