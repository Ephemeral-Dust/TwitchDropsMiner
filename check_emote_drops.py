#!/usr/bin/env python3
"""
Simple emote drop checker for Twitch Drops Miner.
This script checks for new emote drops and how they appear in the API.
"""

import json
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EmoteDropChecker")


async def check_emote_drops():
    """Quick check for emote drops using existing miner infrastructure."""

    try:
        # Import after logging setup
        from twitch import Twitch
        from settings import Settings
        from constants import GQL_OPERATIONS
        import argparse

        logger.info("🎭 Initializing Emote Drop Checker...")

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

        # Try to make a simple GQL request - this will handle login automatically
        logger.info("Testing connection and fetching campaigns...")
        try:
            # This will automatically handle login if needed
            campaigns_response = await twitch.gql_request(
                GQL_OPERATIONS["Campaigns"]
            )
            logger.info("✓ Successfully connected and authenticated")
        except Exception as e:
            logger.error(f"❌ Failed to connect or authenticate: {e}")
            logger.error(
                "Please make sure you have valid login cookies or run the main app first"
            )
            return False

        # Analyze campaigns for emote drops
        emote_drops_found = []
        all_benefit_types = set()

        campaigns = (
            campaigns_response.get("data", {})
            .get("currentUser", {})
            .get("dropCampaigns", [])
        )
        logger.info(f"Found {len(campaigns)} total campaigns")

        for campaign in campaigns:
            campaign_name = campaign.get("name", "Unknown")
            game_name = campaign.get("game", {}).get("displayName", "Unknown")

            # Check time-based drops
            for drop in campaign.get("timeBasedDrops", []):
                drop_name = drop.get("name", "Unknown Drop")

                # Analyze benefits
                benefits = []
                has_emote = False

                for benefit_edge in drop.get("benefitEdges", []):
                    benefit = benefit_edge.get("benefit", {})
                    if benefit:
                        benefit_type = benefit.get(
                            "distributionType", "UNKNOWN"
                        )
                        benefit_name = benefit.get("name", "Unknown")

                        all_benefit_types.add(benefit_type)

                        if benefit_type == "EMOTE":
                            has_emote = True

                        benefits.append(
                            {
                                "name": benefit_name,
                                "type": benefit_type,
                                "id": benefit.get("id", ""),
                                "image_url": benefit.get("imageAssetURL", ""),
                            }
                        )

                if has_emote:
                    emote_drop_info = {
                        "drop_name": drop_name,
                        "campaign_name": campaign_name,
                        "game_name": game_name,
                        "benefits": benefits,
                        "drop_id": drop.get("id", ""),
                        "raw_drop_data": drop,  # Include full data for analysis
                    }
                    emote_drops_found.append(emote_drop_info)
                    logger.info(
                        f"🎭 EMOTE DROP: {drop_name} ({game_name}) - {len(benefits)} benefits"
                    )

        # Save results
        results = {
            "timestamp": datetime.now().isoformat(),
            "emote_drops_found": len(emote_drops_found),
            "all_benefit_types": list(all_benefit_types),
            "emote_drops": emote_drops_found,
        }

        # Save to file
        with open("emote_drops_analysis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info(f"📊 ANALYSIS RESULTS:")
        logger.info(f"  Total campaigns checked: {len(campaigns)}")
        logger.info(f"  Emote drops found: {len(emote_drops_found)}")
        logger.info(
            f"  All benefit types seen: {', '.join(sorted(all_benefit_types))}"
        )

        if emote_drops_found:
            logger.info(f"📋 EMOTE DROPS DETAIL:")
            for i, emote_drop in enumerate(emote_drops_found, 1):
                logger.info(f"  {i}. {emote_drop['drop_name']}")
                logger.info(f"     Game: {emote_drop['game_name']}")
                logger.info(f"     Campaign: {emote_drop['campaign_name']}")
                logger.info(f"     Benefits: {len(emote_drop['benefits'])}")
                for benefit in emote_drop["benefits"]:
                    logger.info(
                        f"       - {benefit['name']} ({benefit['type']})"
                    )
        else:
            logger.info("  No emote drops found in current campaigns")

        logger.info("💾 Detailed results saved to 'emote_drops_analysis.json'")

        # Shutdown
        await twitch.shutdown()
        logger.info("✅ Analysis complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Error during analysis: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(check_emote_drops())
    sys.exit(0 if success else 1)
