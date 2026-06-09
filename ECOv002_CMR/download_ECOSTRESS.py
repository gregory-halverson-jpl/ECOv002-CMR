import argparse
import sys
from typing import List, Union
from datetime import date
import logging

import pandas as pd

from ECOv002_granules import ECOSTRESSGranule

from .constants import *
from .granule_ID import GranuleID
from .download_ECOSTRESS_granule import download_ECOSTRESS_granule
from .ECOSTRESS_CMR_search import ECOSTRESS_CMR_search
from .product_name_from_filename import product_name_from_filename

logger = logging.getLogger(__name__)

def download_ECOSTRESS(
        product: Union[str, List[str]],
        tile: Union[str, List[str]],
        start_date: Union[date, str],
        end_date: Union[date, str] = None,
        orbit: int = None,
        scene: int = None,
        parent_directory: str = DOWNLOAD_DIRECTORY,
        CMR_file_listing_df: pd.DataFrame = None,
        CMR_search_URL: str = CMR_SEARCH_URL) -> List[ECOSTRESSGranule]:
    """
    Searches for and downloads matching ECOSTRESS granules.

    Parameters:
    - product (Union[str, List[str]]): One product code or a list of product codes to download.
    - tile (Union[str, List[str]]): One tile identifier or a list of tile identifiers.
    - start_date (Union[date, str]): Start date for the search window.
    - end_date (Union[date, str], optional): End date for the search window. Defaults to start_date.
    - orbit (int, optional): The orbit number. Defaults to None.
    - scene (int, optional): The scene number. Defaults to None.
    - parent_directory (str, optional): The directory to save the downloaded files. Defaults to ".".
    - CMR_file_listing_df (pd.DataFrame, optional): Optional pre-fetched CMR listing. Defaults to None.
    - CMR_search_URL (str, optional): The URL for CMR search. Defaults to CMR_SEARCH_URL.

    Returns:
    - List[ECOSTRESSGranule]: Downloaded ECOSTRESS granule objects.
    """
    if end_date is None:
        end_date = start_date

    if isinstance(product, str):
        products = [product]
    else:
        products = list(product)

    if isinstance(tile, str):
        tiles = [tile]
    else:
        tiles = list(tile)

    if len(products) == 0:
        raise ValueError("At least one product must be provided")

    if len(tiles) == 0:
        raise ValueError("At least one tile must be provided")

    invalid_products = sorted({p for p in products if p not in CONCEPT_IDS})
    if invalid_products:
        allowed_products = ", ".join(sorted(CONCEPT_IDS))
        invalid_products_text = ", ".join(invalid_products)
        raise ValueError(f"Unknown product type(s): {invalid_products_text}. Allowed products: {allowed_products}")

    products = list(dict.fromkeys(products))
    tiles = list(dict.fromkeys(tiles))

    if CMR_file_listing_df is None:
        CMR_file_listing_df = ECOSTRESS_CMR_search(
            product=products,
            tile=tiles,
            start_date=start_date,
            end_date=end_date,
            orbit=orbit,
            scene=scene,
            CMR_search_URL=CMR_search_URL,
        )

    if CMR_file_listing_df.empty:
        return []

    if "granule" not in CMR_file_listing_df.columns:
        raise ValueError("CMR listing is missing required 'granule' column")

    granule_names = list(dict.fromkeys(CMR_file_listing_df["granule"].dropna().astype(str).tolist()))
    downloaded = []

    for granule_name in granule_names:
        granule_listing = CMR_file_listing_df[CMR_file_listing_df["granule"] == granule_name]
        granule_id = GranuleID(granule_name)
        granule_product = product_name_from_filename(granule_name)

        granule = download_ECOSTRESS_granule(
            product=granule_product,
            tile=granule_id.tile,
            aquisition_date=start_date,
            orbit=granule_id.orbit,
            scene=granule_id.scene,
            parent_directory=parent_directory,
            CMR_file_listing_df=granule_listing,
            CMR_search_URL=CMR_search_URL,
        )
        downloaded.append(granule)

    return downloaded


def main():
    """Command-line interface wrapper for download_ECOSTRESS_granule."""
    parser = argparse.ArgumentParser(
        description="Download ECOSTRESS granules for a date range and open them as ECOSTRESSGranule objects."
    )

    allowed_product_codes = sorted(CONCEPT_IDS)
    allowed_products = ", ".join(allowed_product_codes)

    parser.add_argument("-p", "--product", required=True, type=str, nargs="+",
                        choices=allowed_product_codes,
                        help=f"One or more ECOSTRESS product codes. Allowed values: {allowed_products}.")
    parser.add_argument("-t", "--tile", required=True, type=str, nargs="+",
                        help="One or more Sentinel-2 tile identifiers (e.g., '11SLT').")
    parser.add_argument("-s", "--start-date", required=True, type=str,
                        metavar="YYYY-MM-DD",
                        help="Start date (YYYY-MM-DD).")
    parser.add_argument("-e", "--end-date", required=False, type=str, default=None,
                        metavar="YYYY-MM-DD",
                        help="End date (YYYY-MM-DD). Defaults to --start-date.")
    parser.add_argument("--orbit", type=int, default=None,
                        help="Optional orbit number filter.")
    parser.add_argument("--scene", type=int, default=None,
                        help="Optional scene number filter.")
    parser.add_argument("--parent-directory", type=str, default=DOWNLOAD_DIRECTORY,
                        help="Parent directory where granule files are downloaded.")
    parser.add_argument("--cmr-url", type=str, default=CMR_SEARCH_URL,
                        help="Custom base URL for the CMR search API.")

    args = parser.parse_args()
    selected_products = list(dict.fromkeys(args.product))
    selected_tiles = list(dict.fromkeys(args.tile))
    tile_label = "tile" if len(selected_tiles) == 1 else "tiles"
    date_text = (
        f"on {args.start_date}"
        if args.end_date is None or args.end_date == args.start_date
        else f"from {args.start_date} to {args.end_date}"
    )

    try:
        logger.info(
            f"downloading {', '.join(selected_products)} for {tile_label} {', '.join(selected_tiles)} {date_text}"
        )

        downloaded = download_ECOSTRESS(
            product=selected_products,
            tile=selected_tiles,
            start_date=args.start_date,
            end_date=args.end_date,
            orbit=args.orbit,
            scene=args.scene,
            parent_directory=args.parent_directory,
            CMR_search_URL=args.cmr_url,
        )

        if not downloaded:
            logger.info("No matching granules found for the given criteria.")
            sys.exit(0)

        logger.info(f"Found {len(downloaded)} matching granule(s).")

        logger.info("Download complete.")
        for granule in downloaded:
            logger.info(str(granule))

    except Exception as err:
        logger.info(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()