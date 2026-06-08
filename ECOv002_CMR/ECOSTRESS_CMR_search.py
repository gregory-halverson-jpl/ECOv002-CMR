import argparse
import sys
from typing import Union
import requests
import pandas as pd
import json
import posixpath
from datetime import date
from dateutil import parser

from sentinel_tiles import sentinel_tiles

from .constants import *
from .ECOSTRESS_CMR_search_links import ECOSTRESS_CMR_search_links
from .interpret_ECOSTRESS_URLs import interpret_ECOSTRESS_URLs

def ECOSTRESS_CMR_search(
        product: str, 
        tile: str, 
        start_date: Union[date, str], 
        end_date: Union[date, str] = None,
        orbit: int = None,
        scene: int = None,
        CMR_search_URL: str = CMR_SEARCH_URL) -> pd.DataFrame:
    """
    Search the CMR API for ECOSTRESS granules and return parsed results.

    Args:
        product: ECOSTRESS product code. Allowed values are:
            L2T_LSTE, L2T_STARS, L3T_MET, L3T_SM, L3T_SEB, L3T_JET, L4T_ESI, L4T_WUE.
        tile: Sentinel-2 tile identifier (for example, "11SLT").
        start_date: Start date as a date object or parsable date string.
        end_date: End date as a date object or parsable date string. Defaults to start_date.
        orbit: Optional orbit number filter.
        scene: Optional scene number filter.
        CMR_search_URL: Base URL for CMR search.

    Returns:
        pandas.DataFrame with matched granule metadata.

    Raises:
        ValueError: If product is not one of the allowed product codes.
    """
    # Convert start_date and end_date to date objects if they are strings
    if isinstance(start_date, str):
        start_date = parser.parse(start_date).date()

    if end_date is None:
        end_date = start_date
    elif isinstance(end_date, str):
        end_date = parser.parse(end_date).date()

    if product not in CONCEPT_IDS:
        allowed_products = ", ".join(sorted(CONCEPT_IDS))
        raise ValueError(f"Unknown product type: {product}. Allowed products: {allowed_products}")
    
    concept_ID = CONCEPT_IDS[product]

    # Get the URLs of ECOSTRESS granules using the helper function
    URLs = ECOSTRESS_CMR_search_links(
        concept_ID=concept_ID, 
        tile=tile, 
        start_date=start_date.strftime("%Y-%m-%d"), 
        end_date=end_date.strftime("%Y-%m-%d"), 
        CMR_search_URL=CMR_search_URL
    )

    df = interpret_ECOSTRESS_URLs(
        URLs=URLs,
        orbit=orbit,
        scene=scene
    )

    return df


def main():
    """Command-line interface wrapper for ECOSTRESS_CMR_search."""
    parser = argparse.ArgumentParser(
        description="Search the NASA CMR API for ECOSTRESS granules and map them to Sentinel-2 tiles."
    )
    
    allowed_product_codes = sorted(CONCEPT_IDS)
    allowed_products = ", ".join(allowed_product_codes)

    # Required arguments
    parser.add_argument("-p", "--product", required=True, type=str,
                        choices=allowed_product_codes,
                        help=f"ECOSTRESS product code. Allowed values: {allowed_products}.")
    parser.add_argument("-t", "--tile", required=True, type=str, 
                        help="Sentinel-2 tile identifier (e.g., '10UEV').")
    parser.add_argument("-s", "--start-date", required=True, type=str,
                        metavar="YYYY-MM-DD",
                        help="Start date of the search period (YYYY-MM-DD).")
    
    # Optional arguments
    parser.add_argument("-e", "--end-date", type=str, default=None,
                        metavar="YYYY-MM-DD",
                        help="End date of the search period (YYYY-MM-DD). Defaults to start-date.")
    parser.add_argument("--orbit", type=int, default=None, 
                        help="Optional orbit number filter.")
    parser.add_argument("--scene", type=int, default=None, 
                        help="Optional scene number filter.")
    parser.add_argument("-o", "--output", type=str, default=None, 
                        help="Path to save the output CSV file. If not provided, results print to console.")
    parser.add_argument("--cmr-url", type=str, default=CMR_SEARCH_URL, 
                        help="Custom base URL for the CMR search API.")

    args = parser.parse_args()

    try:
        print(f"Initializing search for {args.product} on tile {args.tile}...")
        
        df = ECOSTRESS_CMR_search(
            product=args.product,
            tile=args.tile,
            start_date=args.start_date,
            end_date=args.end_date,
            orbit=args.orbit,
            scene=args.scene,
            CMR_search_URL=args.cmr_url
        )

        if df.empty:
            print("No matching granules found for the given criteria.")
            sys.exit(0)

        print(f"Success! Found {len(df)} matching items.")

        # Handle output target
        if args.output:
            df.to_csv(args.output, index=False)
            print(f"Results successfully saved to: {args.output}")
        else:
            if "granule" not in df.columns:
                raise ValueError("Expected 'granule' column in search results.")

            # Preserve first-seen ordering while removing duplicates.
            granules = df["granule"].dropna().astype(str).tolist()
            ordered_unique_granules = list(dict.fromkeys(granules))

            print("Granules:")
            for granule in ordered_unique_granules:
                print(granule)

    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()