import requests
import json

BASE_URL = "http://localhost:8000"


def test_get(name: str, path: str):
    url = f"{BASE_URL}{path}"

    print("\n" + "=" * 70)
    print(f"TEST: {name}")
    print(f"URL: {url}")
    print("=" * 70)

    try:
        response = requests.get(url, timeout=10)

        print(f"Status Code: {response.status_code}")

        try:
            data = response.json()
            print("\nResponse:")
            print(json.dumps(data, indent=2))
        except ValueError:
            print("\nResponse:")
            print(response.text)

        if response.status_code == 200:
            print("\nRESULT: PASS")
        else:
            print("\nRESULT: FAIL")

    except requests.exceptions.ConnectionError:
        print("\nRESULT: FAIL")
        print("Cannot connect to backend.")
        print("Make sure Docker containers are running.")

    except requests.exceptions.Timeout:
        print("\nRESULT: FAIL")
        print("Request timed out.")

    except Exception as e:
        print("\nRESULT: FAIL")
        print(f"Error: {e}")


if __name__ == "__main__":

    print("\nFLEET MANAGEMENT BACKEND - HTTP TESTS")

    test_get(
        "Root Endpoint",
        "/"
    )

    test_get(
        "Health Check",
        "/health"
    )

    test_get(
        "Current Fleet Data",
        "/fleet/current"
    )

    print("\n" + "=" * 70)
    print("HTTP TESTING COMPLETED")
    print("=" * 70)
