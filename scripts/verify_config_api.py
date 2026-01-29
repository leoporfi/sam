import requests

BASE_URL = "http://127.0.0.1:8000/api"


def test_config_api():
    print("Testing GET /api/config...")
    try:
        response = requests.get(f"{BASE_URL}/config")
        if response.status_code == 200:
            configs = response.json()
            print(f"Success! Found {len(configs)} configuration items.")
            if configs:
                print(f"First item: {configs[0]}")
        else:
            print(f"Failed to get configs: {response.status_code} - {response.text}")
            return

        # Test Update
        if configs:
            real_key = configs[0]["Clave"]
            original_value = configs[0]["Valor"]

            print(f"\nTesting PUT /api/config/{real_key}...")
            # Use a numeric value if it's a numeric key, or just a string
            test_val = "999" if real_key.endswith(("_SEG", "_MIN", "_SIZE", "_COUNT")) else "test_val"

            update_payload = {"value": test_val}
            put_response = requests.put(f"{BASE_URL}/config/{real_key}", json=update_payload)

            if put_response.status_code == 200:
                print(f"Update success: {put_response.json()}")

                # Restore original value
                requests.put(f"{BASE_URL}/config/{real_key}", json={"value": original_value})
                print("Restored original value.")
            else:
                print(f"Update failed: {put_response.status_code} - {put_response.text}")

    except Exception as e:
        print(f"Error connecting to API: {e}")
        print("Is the server running at http://127.0.0.1:8000?")


if __name__ == "__main__":
    test_config_api()
