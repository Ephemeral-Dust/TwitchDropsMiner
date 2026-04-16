#!/usr/bin/env python3
"""
Fetches currently active/upcoming Twitch drop campaigns and their drops,
then writes a clean summary to drops.json.

Uses the existing cookies.jar for authentication — no GUI or websocket needed.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import aiohttp
from yarl import URL

from constants import GQL_OPERATIONS, COOKIES_PATH, ClientType, JsonType

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("DropAnalysis")

GQL_URL = "https://gql.twitch.tv/gql"
CLIENT = ClientType.ANDROID_APP


def _make_headers(access_token: str) -> dict[str, str]:
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
        "Accept-Language": "en-US",
        "Authorization": f"OAuth {access_token}",
        "Cache-Control": "no-cache",
        "Client-Id": CLIENT.CLIENT_ID,
        "Origin": str(CLIENT.CLIENT_URL),
        "Pragma": "no-cache",
        "Referer": str(CLIENT.CLIENT_URL),
        "User-Agent": CLIENT.USER_AGENT,
    }


async def _get_access_token(session: aiohttp.ClientSession) -> str:
    """Extract the auth-token from the loaded cookie jar."""
    jar = cast(aiohttp.CookieJar, session.cookie_jar)
    cookie = jar.filter_cookies(CLIENT.CLIENT_URL)
    if "auth-token" not in cookie:
        raise RuntimeError(
            f"No auth-token cookie found in {COOKIES_PATH}. "
            "Run the main app and log in first."
        )
    return cookie["auth-token"].value


async def _gql(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    op: JsonType,
) -> JsonType:
    async with session.post(GQL_URL, json=op, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


def _fmt_time(iso: str | None) -> str | None:
    if iso is None:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    except Exception:
        return iso


def _summarise_campaign(c: JsonType) -> dict[str, Any]:
    game: JsonType = c.get("game") or {}
    drops_raw: list[JsonType] = c.get("timeBasedDrops") or []

    drops: list[dict[str, Any]] = []
    for d in drops_raw:
        self_edge: JsonType = d.get("self") or {}
        benefits = [
            {
                "name": be.get("benefit", {}).get("name"),
                "type": be.get("benefit", {}).get("distributionType"),
                "image": be.get("benefit", {}).get("imageAssetURL"),
            }
            for be in (d.get("benefitEdges") or [])
            if be.get("benefit")
        ]
        required_min: int = d.get("requiredMinutesWatched", 0)
        current_min: int = self_edge.get("currentMinutesWatched") or 0
        drops.append(
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "starts_at": _fmt_time(d.get("startAt")),
                "ends_at": _fmt_time(d.get("endAt")),
                "required_minutes": required_min,
                "progress_minutes": current_min,
                "progress_pct": (
                    round(current_min / required_min * 100, 1)
                    if required_min > 0
                    else None
                ),
                "is_claimed": self_edge.get("isClaimed", False),
                "can_claim": (
                    self_edge.get("dropInstanceID") is not None
                    and not self_edge.get("isClaimed", False)
                ),
                "benefits": benefits,
            }
        )

    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "status": c.get("status"),
        "game": game.get("displayName") or game.get("name"),
        "starts_at": _fmt_time(c.get("startAt")),
        "ends_at": _fmt_time(c.get("endAt")),
        "drops": drops,
    }


async def main() -> None:
    if not COOKIES_PATH.exists():
        raise FileNotFoundError(
            f"Cookies file not found at {COOKIES_PATH}. "
            "Run the main app and log in first."
        )

    jar = aiohttp.CookieJar()
    jar.load(COOKIES_PATH)

    async with aiohttp.ClientSession(
        cookie_jar=jar,
        headers={"User-Agent": CLIENT.USER_AGENT},
    ) as session:
        access_token = await _get_access_token(session)
        headers = _make_headers(access_token)
        logger.info("Authenticated — fetching campaigns…")

        # 1. Fetch the campaigns list (ACTIVE + UPCOMING)
        campaigns_resp = await _gql(
            session, headers, GQL_OPERATIONS["Campaigns"]
        )
        campaigns_raw: list[JsonType] = (
            campaigns_resp.get("data", {})
            .get("currentUser", {})
            .get("dropCampaigns")
            or []
        )
        active_statuses = {"ACTIVE", "UPCOMING"}
        campaigns_raw = [
            c for c in campaigns_raw if c.get("status") in active_statuses
        ]
        logger.info(
            f"Found {len(campaigns_raw)} active/upcoming campaign(s) from dashboard"
        )

        # 2. Fetch in-progress inventory so we can overlay personal progress
        inventory_resp = await _gql(
            session, headers, GQL_OPERATIONS["Inventory"]
        )
        inventory_section: JsonType = (
            inventory_resp.get("data", {})
            .get("currentUser", {})
            .get("inventory")
            or {}
        )
        in_progress_raw: list[JsonType] = (
            inventory_section.get("dropCampaignsInProgress") or []
        )
        # Build a quick lookup: campaign_id -> in-progress drops (with self-edge data)
        in_progress_map: dict[str, JsonType] = {
            c["id"]: c for c in in_progress_raw
        }
        logger.info(
            f"Found {len(in_progress_raw)} campaign(s) in personal inventory"
        )

        # Merge in-progress data into the campaigns list; add any inventory-only campaigns
        campaigns_by_id: dict[str, JsonType] = {
            c["id"]: c for c in campaigns_raw
        }
        for cid, ip_campaign in in_progress_map.items():
            if cid not in campaigns_by_id:
                campaigns_by_id[cid] = ip_campaign
            else:
                # Overlay self-edge data onto timeBasedDrops from the dashboard campaign
                ip_drops: dict[str, JsonType] = {
                    d["id"]: d
                    for d in (ip_campaign.get("timeBasedDrops") or [])
                }
                for drop in campaigns_by_id[cid].get("timeBasedDrops") or []:
                    if (
                        drop["id"] in ip_drops
                        and "self" in ip_drops[drop["id"]]
                    ):
                        drop["self"] = ip_drops[drop["id"]]["self"]

        # 3. Summarise
        now = datetime.now(timezone.utc)
        summaries: list[dict[str, Any]] = []
        for campaign in sorted(
            campaigns_by_id.values(),
            key=lambda c: (c.get("status") != "ACTIVE", c.get("endAt") or ""),
        ):
            summaries.append(_summarise_campaign(campaign))

        output = {
            "generated_at": now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "total_campaigns": len(summaries),
            "campaigns": summaries,
        }

        out_path = Path("drops.json")
        out_path.write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(
            f"Written {len(summaries)} campaign(s) to {out_path.resolve()}"
        )


if __name__ == "__main__":
    asyncio.run(main())
