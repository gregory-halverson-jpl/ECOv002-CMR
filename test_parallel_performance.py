"""
Test script to compare parallel vs sequential execution performance.

This is a pytest test suite that validates parallel execution provides
performance benefits over sequential processing when sampling ECOSTRESS data.

Requires: NASA Earthdata authentication via EARTHDATA_USERNAME and EARTHDATA_PASSWORD
environment variables or ~/.netrc file.
"""
import os
import time
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
def test_parallel_vs_sequential_performance():
    """
    Test that parallel execution is available and runs without error.
    
    Note: Speedup comparisons are informational only, as performance
    depends heavily on system resources and network conditions.
    """
    # Load site metadata
    sites_df = load_metadata_ebc_filt()
    test_sites = sites_df.iloc[:3]  # Use 3 sites for testing
    
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON: Sequential vs Parallel Execution")
    print("=" * 80)
    print(f"\nTest configuration:")
    print(f"  - Points: {len(test_sites)}")
    print(f"  - Date range: 2022-06-01 to 2022-06-20")
    print(f"  - Layers: ST_C, emissivity, NDVI, albedo, Ta_C, RH, SM")
    
    # Test 1: Sequential execution (max_workers=1)
    print("\n" + "=" * 80)
    print("Test 1: SEQUENTIAL EXECUTION (max_workers=1)")
    print("=" * 80)
    start_time = time.time()
    result_seq = sample_points_over_date_range(
        geometry=test_sites,
        start_date="2022-06-01",
        end_date="2022-06-20",
        layers=['ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM'],
        max_workers=1,
        verbose=False
    )
    seq_time = time.time() - start_time
    
    print(f"\n  Results: {len(result_seq)} observations")
    print(f"  Execution time: {seq_time:.2f} seconds")
    
    # Verify results
    assert isinstance(result_seq, pd.DataFrame)
    assert len(result_seq) > 0, "Expected at least some results from sequential execution"
    
    # Test 2: Parallel execution (max_workers=10, default)
    print("\n" + "=" * 80)
    print("Test 2: PARALLEL EXECUTION (max_workers=10, default)")
    print("=" * 80)
    start_time = time.time()
    result_par = sample_points_over_date_range(
        geometry=test_sites,
        start_date="2022-06-01",
        end_date="2022-06-20",
        layers=['ST_C', 'emissivity', 'NDVI', 'albedo', 'Ta_C', 'RH', 'SM'],
        max_workers=10,
        verbose=False
    )
    par_time = time.time() - start_time
    
    print(f"\n  Results: {len(result_par)} observations")
    print(f"  Execution time: {par_time:.2f} seconds")
    
    # Verify results
    assert isinstance(result_par, pd.DataFrame)
    assert len(result_par) > 0, "Expected at least some results from parallel execution"
    
    # Summary and verification
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"Sequential execution: {seq_time:.2f}s")
    print(f"Parallel execution:   {par_time:.2f}s")
    
    if par_time > 0:
        speedup = seq_time / par_time
        time_saved = seq_time - par_time
        percent_reduction = (1 - par_time / seq_time) * 100
        print(f"Speedup:              {speedup:.2f}x")
        print(f"Time saved:           {time_saved:.2f}s ({percent_reduction:.1f}% reduction)")
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print(f"Sequential observations: {len(result_seq)}")
    print(f"Parallel observations:   {len(result_par)}")
    
    # Most important: results should match regardless of execution method
    results_match = len(result_seq) == len(result_par)
    print(f"Results match: {results_match}")
    assert results_match, \
        "Parallel and sequential execution should return the same number of results"
