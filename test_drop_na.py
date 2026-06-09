"""
Test script to demonstrate drop_na parameter functionality.

This is a pytest test suite that validates the drop_na parameter behavior
when sampling ECOSTRESS data at multiple points across a date range.

Requires: NASA Earthdata authentication via EARTHDATA_USERNAME and EARTHDATA_PASSWORD
environment variables or ~/.netrc file.
"""
import os
import pytest
import geopandas as gpd
import pandas as pd
from ECOv002_calval_tables import load_metadata_ebc_filt
from ECOv002_CMR import sample_points_over_date_range


# Skip these tests if running in CI without proper credentials configured
SKIP_REASON = "Requires NASA Earthdata authentication (EARTHDATA_USERNAME and EARTHDATA_PASSWORD)"
SHOULD_SKIP = (
    os.environ.get("CI") == "true" and 
    not (os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))
)


@pytest.mark.skipif(SHOULD_SKIP, reason=SKIP_REASON)
def test_drop_na_parameter():
    """
    Test drop_na parameter functionality with default behavior.
    
    Validates that:
    - drop_na=True (default) removes rows with no valid data
    - Results are properly filtered
    """
    # Load site metadata
    sites_df = load_metadata_ebc_filt()
    test_sites = sites_df.iloc[:3]  # Use 3 sites for testing
    
    print("\n" + "=" * 80)
    print("TEST 1: drop_na=True (default) - Removes rows with no valid data")
    print("=" * 80)
    
    result_with_drop = sample_points_over_date_range(
        geometry=test_sites,
        start_date="2022-06-01",
        end_date="2022-06-20",
        layers=['ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM'],
        drop_na=True,  # Default behavior
        verbose=True
    )
    
    print(f"\nResult: {len(result_with_drop)} observations")
    print(f"Unique granules: {result_with_drop['granule'].nunique()}")
    
    # Verify we got results
    assert isinstance(result_with_drop, pd.DataFrame)
    assert len(result_with_drop) > 0, "Expected at least some results with drop_na=True"
    assert 'granule' in result_with_drop.columns


@pytest.mark.skipif(SHOULD_SKIP, reason=SKIP_REASON)
def test_drop_na_keeps_all_rows():
    """
    Test drop_na=False behavior.
    
    Validates that:
    - drop_na=False keeps all rows including those with no data
    - Results with drop_na=False >= results with drop_na=True
    """
    # Load site metadata
    sites_df = load_metadata_ebc_filt()
    test_sites = sites_df.iloc[:3]  # Use 3 sites for testing
    
    print("\n" + "=" * 80)
    print("TEST 2: drop_na=False - Keeps all rows including those with no data")
    print("=" * 80)
    
    # First get results with drop_na=True
    result_with_drop = sample_points_over_date_range(
        geometry=test_sites,
        start_date="2022-06-01",
        end_date="2022-06-20",
        layers=['ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM'],
        drop_na=True,
        verbose=False
    )
    
    # Now get results with drop_na=False
    result_without_drop = sample_points_over_date_range(
        geometry=test_sites,
        start_date="2022-06-01",
        end_date="2022-06-20",
        layers=['ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM'],
        drop_na=False,
        verbose=True
    )
    
    print(f"\nResult with drop_na=True:  {len(result_with_drop)} observations")
    print(f"Result with drop_na=False: {len(result_without_drop)} observations")
    print(f"Unique granules: {result_without_drop['granule'].nunique()}")
    
    # Verify results
    assert isinstance(result_without_drop, pd.DataFrame)
    assert len(result_without_drop) > 0, "Expected at least some results with drop_na=False"
    assert len(result_without_drop) >= len(result_with_drop), \
        "drop_na=False should return >= rows than drop_na=True"
    
    rows_filtered = len(result_without_drop) - len(result_with_drop)
    print(f"\nRows filtered by drop_na=True: {rows_filtered}")
    
    # Show example of dropped rows if any were filtered
    if rows_filtered > 0:
        print("\n" + "=" * 80)
        print("EXAMPLE OF FILTERED ROWS (rows with all NaN in sampled variables)")
        print("=" * 80)
        
        # Find rows that were dropped
        merged = result_without_drop.merge(
            result_with_drop[['granule', 'point_index']], 
            on=['granule', 'point_index'], 
            how='left', 
            indicator=True
        )
        dropped_rows = merged[merged['_merge'] == 'left_only']
        
        if len(dropped_rows) > 0:
            cols = ['timestamp', 'ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM']
            available_cols = [c for c in cols if c in dropped_rows.columns]
            print(dropped_rows[available_cols].head())
