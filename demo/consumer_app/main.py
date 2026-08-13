import requests

def fetch_user_profile(user_id: str):
    """
    Fetches user profile details using user_id keyword arg.
    """
    url = "/api/v1/users"
    params = {"user_id": user_id}
    response = requests.get(url, params=params)
    return response.json()

if __name__ == "__main__":
    profile = fetch_user_profile(user_id="usr_12345")
    print("Fetched profile:", profile)
