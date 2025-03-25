import requests
import time
import re

# qBittorrent Settings
QB_URL = "http://127.0.0.1:8080"
QB_USERNAME = "admin"
QB_PASSWORD = "password"

def login_qbittorrent():
    """Logs into qBittorrent and returns the session."""
    session = requests.Session()
    data = {"username": QB_USERNAME, "password": QB_PASSWORD}
    
    res = session.post(f"{QB_URL}/api/v2/auth/login", data=data)
    if res.text != "Ok.":
        print(f"Error: Unable to connect to qBittorrent. Response: {res.text}")
        return None

    print("Connected to qBittorrent.")
    return session

def search_movie(session, movie, quality, audio_type, year):
    """Searches for a movie in qBittorrent."""
    print(f"Searching for: {movie}...")
    time.sleep(2)

    data = {"pattern": movie, "plugins": "all", "category": "movies"}

    try:
        res = session.post(f"{QB_URL}/api/v2/search/start", data=data)
        if res.status_code != 200:
            print(f"Error: Search failed. Response: {res.text}")
            return None

        search_id = res.json().get("id")
        if not search_id:
            print("Error: Could not retrieve search ID.")
            return None

        time.sleep(5)
        res = session.get(f"{QB_URL}/api/v2/search/results?id={search_id}")
        results = res.json().get("results", [])

        if not results:
            print(f"No torrents found for: {movie}")
            return None

        filtered_results = [torrent for torrent in results if (
            check_quality(torrent.get('fileName', ''), quality) and
            check_audio_type(torrent.get('fileName', ''), audio_type) and
            check_year(torrent.get('fileName', ''), year)
        )]

        return filtered_results if filtered_results else None
    
    except Exception as e:
        print(f"Error processing response: {e}")
        return None

def check_quality(file_name, quality):
    if not quality:
        return True
    return bool(re.search(re.escape(quality), file_name, re.IGNORECASE))

def check_audio_type(file_name, audio_type):
    if not audio_type:
        return True
    return bool(re.search(re.escape(audio_type), file_name, re.IGNORECASE))

def check_year(file_name, year):
    if not year:
        return True
    return bool(re.search(rf"\b{year}\b", file_name))

def add_torrent(session, magnet_link):
    """Adds a torrent to qBittorrent."""
    try:
        res = session.post(f"{QB_URL}/api/v2/torrents/add", data={"urls": magnet_link})
        return res.status_code == 200
    except Exception as e:
        print(f"Error adding torrent: {e}")
        return False

def main():
    """Handles login, search, and downloading torrents."""
    session = login_qbittorrent()
    if not session:
        return

    movie = input("Enter movie name: ").strip()
    quality = input("Enter desired quality (e.g., 4K, 1080p) or leave blank: ").strip()
    audio_type = input("Enter audio type (dubbed, subtitled, dual audio) or leave blank: ").strip()
    year = input("Enter movie year (optional) or leave blank: ").strip()

    torrents = search_movie(session, movie, quality, audio_type, year)
    if torrents:
        print(f"Found {len(torrents)} matching torrents.")
        for i, torrent in enumerate(torrents[:5], start=1):  # Show up to 5 results
            print(f"{i}. {torrent.get('fileName')}")

        choice = int(input("Select a torrent number to download: ")) - 1
        if 0 <= choice < len(torrents):
            if add_torrent(session, torrents[choice].get("fileUrl")):
                print("Torrent added successfully!")
            else:
                print("Failed to add torrent.")
    else:
        print("No torrents found matching the criteria.")

if __name__ == "__main__":
    main()
