import argparse
import sys
from typing import Union
from os.path import join
from datetime import date
import posixpath
import pandas as pd

from ECOv002_granules import ECOSTRESSGranule, open_granule

from .constants import *
from .granule_ID import GranuleID
from .download_file import download_file
from .download_ECOSTRESS_granule_files import download_ECOSTRESS_granule_files
from .ECOSTRESS_CMR_search import ECOSTRESS_CMR_search

def download_ECOSTRESS_granule(
        product: str, 
        tile: str, 
        aquisition_date: Union[date, str], 
        orbit: int = None,
        scene: int = None,
        parent_directory: str = DOWNLOAD_DIRECTORY,
        CMR_file_listing_df: pd.DataFrame = None,
        CMR_search_URL: str = CMR_SEARCH_URL) -> ECOSTRESSGranule:
    """
    Downloads an ECOSTRESS granule based on the provided parameters and returns the granule object.

    Parameters:
    - product (str): The product type to download.
    - tile (str): The tile identifier.
    - aquisition_date (Union[date, str]): The date of acquisition.
    - orbit (int, optional): The orbit number. Defaults to None.
    - scene (int, optional): The scene number. Defaults to None.
    - parent_directory (str, optional): The directory to save the downloaded files. Defaults to ".".
    - CMR_file_listing_df (pd.DataFrame, optional): DataFrame containing file listings from CMR. Defaults to None.
    - CMR_search_URL (str, optional): The URL for CMR search. Defaults to CMR_SEARCH_URL.

    Returns:
    - ECOSTRESSGranule: The downloaded ECOSTRESS granule object.
    """
    directory = download_ECOSTRESS_granule_files(
        product=product,
        tile=tile,
        aquisition_date=aquisition_date,
        orbit=orbit,
        scene=scene,
        parent_directory=parent_directory,
        CMR_file_listing_df=CMR_file_listing_df,
        CMR_search_URL=CMR_search_URL
    )

    granule = open_granule(directory)

    return granule


def main():
    """Command-line interface wrapper for download_ECOSTRESS_granule."""
    parser = argparse.ArgumentParser(
        description="Download a single ECOSTRESS granule and open it as an ECOSTRESSGranule object."
    )

    allowed_product_codes = sorted(CONCEPT_IDS)
    allowed_products = ", ".join(allowed_product_codes)

    parser.add_argument("-p", "--product", required=True, type=str,
                        choices=allowed_product_codes,
                        help=f"ECOSTRESS product code. Allowed values: {allowed_products}.")
    parser.add_argument("-t", "--tile", required=True, type=str,
                        help="Sentinel-2 tile identifier (e.g., '11SLT').")
    parser.add_argument("-d", "--acquisition-date", required=True, type=str,
                        metavar="YYYY-MM-DD",
                        help="Acquisition date (YYYY-MM-DD).")
    parser.add_argument("--orbit", type=int, default=None,
                        help="Optional orbit number filter.")
    parser.add_argument("--scene", type=int, default=None,
                        help="Optional scene number filter.")
    parser.add_argument("--parent-directory", type=str, default=DOWNLOAD_DIRECTORY,
                        help="Parent directory where granule files are downloaded.")
    parser.add_argument("--cmr-url", type=str, default=CMR_SEARCH_URL,
                        help="Custom base URL for the CMR search API.")

    args = parser.parse_args()

    try:
        print(
            f"Downloading {args.product} for tile {args.tile} on {args.acquisition_date}..."
        )

        listing = ECOSTRESS_CMR_search(
            product=args.product,
            tile=args.tile,
            start_date=args.acquisition_date,
            end_date=args.acquisition_date,
            orbit=args.orbit,
            scene=args.scene,
            CMR_search_URL=args.cmr_url,
        )

        if listing.empty:
            print("No matching granules found for the given criteria.")
            sys.exit(0)

        granule_names = list(dict.fromkeys(listing["granule"].dropna().astype(str).tolist()))
        print(f"Found {len(granule_names)} matching granule(s).")

        downloaded = []
        for granule_name in granule_names:
            granule_listing = listing[listing["granule"] == granule_name]
            granule_id = GranuleID(granule_name)
            print(f"Downloading granule: {granule_name}")

            granule = download_ECOSTRESS_granule(
                product=args.product,
                tile=args.tile,
                aquisition_date=args.acquisition_date,
                orbit=granule_id.orbit,
                scene=granule_id.scene,
                parent_directory=args.parent_directory,
                CMR_file_listing_df=granule_listing,
                CMR_search_URL=args.cmr_url,
            )
            downloaded.append(str(granule))

        print("Download complete.")
        for item in downloaded:
            print(item)

    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()