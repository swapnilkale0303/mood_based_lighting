import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Function to load credentials from a file
def load_credentials(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return None

# Function to save credentials to a file
def save_credentials(filename, credentials):
    with open(filename, 'w') as file:
        json.dump(credentials, file)

# Handler for HTTP requests
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Authorization successful! You can close this window now.')

            # Ensure 'code=' exists before splitting
            if 'code=' in self.path:
                self.server.auth_code = self.path.split('code=')[1].split('&')[0]  # Extract the code safely
                print(f"Authorization code received: {self.server.auth_code}")
            else:
                self.server.auth_code = None
                print("Error: Authorization code not found in the callback URL.")
        else:
            self.send_response(404)
            self.end_headers()

# Start the local server in a separate thread
def start_server():
    server = HTTPServer(('localhost', 8888), RequestHandler)
    server.auth_code = None
    print("Starting local server on http://localhost:8888/callback")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

# Get user credentials
username = input("Enter your username: ")
credentials_file = f'{username}_spotify_credentials.json'

# Load existing credentials or prompt the user for new ones if not found
credentials = load_credentials(credentials_file)
if credentials:
    print("Loaded credentials from file:")
    print(credentials)

# Create a SpotifyOAuth instance
sp_oauth = SpotifyOAuth(
    client_id=credentials['client_id'] if credentials else input("Enter your Client ID: "),
    client_secret=credentials['client_secret'] if credentials else input("Enter your Client Secret: "),
    redirect_uri='http://localhost:8888/callback',
    scope='user-read-recently-played user-read-playback-state',
    cache_path=credentials_file
)

# Check if a token is available
token_info = sp_oauth.get_cached_token()

if not token_info:
    # Start the local server to handle redirect
    server = start_server()

    # If no token is available, prompt the user to authorize
    auth_url = sp_oauth.get_authorize_url()
    print(f'Please go to the following URL and authorize: {auth_url}')
    
    # Wait for the authorization code
    while server.auth_code is None:
        pass  # Wait until the server sets the authorization code

    # Get the token using the authorization code
    token_info = sp_oauth.get_access_token(server.auth_code)

    # Save the access token and refresh token
    credentials = {
        'client_id': sp_oauth.client_id,
        'client_secret': sp_oauth.client_secret,
        'access_token': token_info['access_token'],
        'refresh_token': token_info.get('refresh_token')
    }
    save_credentials(credentials_file, credentials)
else:
    print("Access token loaded from cache.")

# Check if the token needs refreshing
if sp_oauth.is_token_expired(token_info):
    print("Access token expired, refreshing...")
    try:
        token_info = sp_oauth.refresh_access_token(credentials['refresh_token'])
        credentials['access_token'] = token_info['access_token']
        # If a new refresh token is returned, update it
        if 'refresh_token' in token_info:
            credentials['refresh_token'] = token_info['refresh_token']
        save_credentials(credentials_file, credentials)
        print("Tokens refreshed successfully.")
    except spotipy.oauth2.SpotifyOauthError as e:
        print(f"Error refreshing token: {e}")
        exit()

# Create a Spotify API client
sp = spotipy.Spotify(auth=token_info['access_token'])

# Get the user's recently played tracks
try:
    results = sp.current_user_recently_played(limit=10)
    tracks = results['items']

    # Define a simple mood dictionary (You can expand this as needed)
    mood_mapping = {
        'happy': ['happy', 'joyful', 'upbeat', 'fun'],
        'sad': ['sad', 'melancholic', 'blue', 'depressed'],
        'neutral': ['calm', 'neutral', 'chill', 'mellow']
    }

    # Function to determine mood based on track name or artist
    def determine_mood(track_name):
        for mood, keywords in mood_mapping.items():
            if any(keyword in track_name.lower() for keyword in keywords):
                return mood
        return 'neutral'  # Default mood if none match

    # Track moods
    track_moods = []
    for item in tracks:
        track_name = item['track']['name']
        mood = determine_mood(track_name)
        track_moods.append(mood)
        print(f"Track: {track_name}, Mood: {mood}")

    # Calculate the overall mood
    mood_count = Counter(track_moods)
    overall_mood = mood_count.most_common(1)[0][0] if mood_count else 'neutral'

    print(f"\nOverall Mood: {overall_mood}")

except spotipy.exceptions.SpotifyException as e:
    print(f"Error retrieving tracks: {e}")
