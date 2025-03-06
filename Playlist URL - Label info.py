import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

# Spotify API credentials
CLIENT_ID = '02189ec7b8ef464fa1df84114ba1178c'
CLIENT_SECRET = 'fc6802e2b0c9454fb730c644daacc87d'

# Authenticate with Spotify
try:
    client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
except Exception as e:
    print(f"Failed to authenticate with Spotify API: {e}")
    exit()

def get_playlist_id(playlist_url):
    """Extract the playlist ID from the URL."""
    try:
        match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid Spotify playlist URL.")
    except Exception as e:
        print(f"Error extracting playlist ID: {e}")
        return None

def analyze_playlist(playlist_url):
    """Analyze the playlist and extract song names and record labels."""
    playlist_id = get_playlist_id(playlist_url)
    if not playlist_id:
        return
    
    try:
        results = sp.playlist_tracks(playlist_id, limit=100)  # Fetch first 100 tracks
        tracks = results['items']
        
        # Handle pagination to fetch up to 1000 tracks
        while results['next'] and len(tracks) < 1000:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        print("\nAnalyzing playlist...\n")
        
        total_songs = 0
        non_epidemic_songs = []
        epidemic_songs = []
        
        for idx, item in enumerate(tracks, start=1):  # Lưu thứ tự bài hát trong playlist gốc
            track = item['track']
            if not track:
                print(f"Skipping invalid track at position {idx}.")
                continue
            
            song_name = track.get('name', 'Unknown Song')
            artist_name = track['artists'][0]['name'] if track.get('artists') else 'Unknown Artist'
            
            # Get album details to fetch the record label
            try:
                album_id = track['album']['id']
                album_details = sp.album(album_id)
                record_label = album_details.get('label', 'Unknown')
            except Exception as e:
                print(f"Error fetching album details for song '{song_name}': {e}")
                record_label = 'Unknown'
            
            print(f"Song: {song_name}")
            print(f"Artist: {artist_name}")
            print(f"Record Label: {record_label}")
            print("-" * 40)
            
            total_songs += 1
            
            # Check if "epidemic" is in the record label name (case-insensitive)
            if "epidemic" in record_label.lower():
                epidemic_songs.append((idx, song_name, artist_name, record_label))  # Lưu thứ tự bài hát có "epidemic"
            else:
                non_epidemic_songs.append((idx, song_name, artist_name, record_label))  # Lưu thứ tự bài hát không có "epidemic"
        
        # Print total number of songs
        print(f"\nTotal number of songs in the playlist: {total_songs}")
        
        # Tự động ưu tiên thông báo danh sách có số lượng ít hơn
        if len(epidemic_songs) < len(non_epidemic_songs):
            print("\nSongs WITH 'epidemic' in the record label (fewer in number):")
            for song_info in epidemic_songs:
                print(f"Position: {song_info[0]}, Song: {song_info[1]}, Artist: {song_info[2]}, Record Label: {song_info[3]}")
            print(f"\nTotal number of songs WITH 'epidemic' in the label: {len(epidemic_songs)}")
        else:
            print("\nSongs WITHOUT 'epidemic' in the record label (fewer in number):")
            for song_info in non_epidemic_songs:
                print(f"Position: {song_info[0]}, Song: {song_info[1]}, Artist: {song_info[2]}, Record Label: {song_info[3]}")
            print(f"\nTotal number of songs WITHOUT 'epidemic' in the label: {len(non_epidemic_songs)}")
    
    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    while True:
        playlist_url = input("Enter the Spotify playlist URL (or type 'exit' to quit): ").strip()
        if playlist_url.lower() == 'exit':
            print("Exiting the script. Goodbye!")
            break
        
        if not playlist_url:
            print("Please enter a valid playlist URL.")
            continue
        
        analyze_playlist(playlist_url)
        
        rerun = input("\nDo you want to analyze another playlist? (yes/no): ").strip().lower()
        if rerun != 'yes':
            print("Exiting the script. Goodbye!")
            break

if __name__ == "__main__":
    main()