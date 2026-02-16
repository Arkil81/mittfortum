"""Test script to check which resolution parameters work with Fortum API."""

import asyncio
import json
from datetime import datetime, timedelta

# Test different resolution values
RESOLUTIONS_TO_TEST = [
    "PER_15_MIN",
    "FIFTEEN_MINUTE", 
    "QUARTER_HOUR",
    "15MIN",
    "HOUR",
    "DAY",
]

async def test_resolution(resolution: str) -> dict:
    """Test a specific resolution parameter."""
    from_date = datetime.now() - timedelta(days=2)
    to_date = datetime.now()
    
    metering_point_no = "1056422"  # From your session data
    
    # Build the tRPC URL
    from custom_components.mittfortum.api.endpoints import APIEndpoints
    
    try:
        url = APIEndpoints.get_time_series_url(
            locale="FI",
            metering_point_nos=[metering_point_no],
            from_date=from_date,
            to_date=to_date,
            resolution=resolution,
        )
        
        return {
            "resolution": resolution,
            "url": url,
            "status": "URL built successfully"
        }
    except Exception as e:
        return {
            "resolution": resolution,
            "status": "Failed",
            "error": str(e)
        }

async def main():
    """Test all resolutions."""
    print("Testing different resolution parameters for Fortum API...")
    print("=" * 80)
    
    results = []
    for resolution in RESOLUTIONS_TO_TEST:
        result = await test_resolution(resolution)
        results.append(result)
        print(f"\nResolution: {resolution}")
        print(f"  Status: {result['status']}")
        if 'error' in result:
            print(f"  Error: {result['error']}")
        if 'url' in result:
            # Extract the resolution from URL to show what was sent
            import urllib.parse
            parsed = urllib.parse.urlparse(result['url'])
            params = urllib.parse.parse_qs(parsed.query)
            if 'input' in params:
                input_data = json.loads(params['input'][0])
                api_resolution = input_data.get('0', {}).get('json', {}).get('resolution')
                print(f"  API Resolution: {api_resolution}")
    
    print("\n" + "=" * 80)
    print("\nSummary:")
    print(json.dumps(results, indent=2))
    
    print("\n\nNote: This only tests URL building. To test actual API calls,")
    print("you need to restart Home Assistant and check the logs for:")
    print("  'Successfully fetched X records with resolution: Y'")

if __name__ == "__main__":
    asyncio.run(main())
