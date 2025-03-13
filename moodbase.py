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

# Function to determine mood based on track's audio features (valence and energy)
def determine_mood(valence, energy):
    if valence > 0.6:
        if energy > 0.7:
            return 'happy'
        else:
            return 'calm'
    elif valence < 0.4:
        if energy > 0.7:
            return 'angry'
        else:
            return 'sad'
    else:
        return 'neutral'  # For mid-range valence and energy

# Get user credentials
username = input("Enter your username: ")
credentials_file = f'{username}_spotify_credentials.json'

# Load existing credentials or prompt the user for new ones if not found
credentials = load_credentials(credentials_file)

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
    # If no token is available, prompt the user to authorize
    auth_url = sp_oauth.get_authorize_url()
    print(f'Please go to the following URL and authorize: {auth_url}')

    # Start local server for redirect
    print("Starting local server for redirect...")

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if 'code=' in self.path:  # Ensure that 'code=' exists in the path
                self.server.auth_code = self.path.split('code=')[1]  # Extract the code
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Authorization successful! You can close this window.')
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid request. No authorization code found.')

    httpd = HTTPServer(('localhost', 8888), OAuthHandler)
    threading.Thread(target=httpd.serve_forever).start()

    print("Waiting for authorization...")

    # Wait for the user to authorize
    while not hasattr(httpd, 'auth_code'):
        pass

    response_code = httpd.auth_code
    # Get the token and save it
    token_info = sp_oauth.get_access_token(response_code)

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
    
    track_moods = []
    track_ids = [item['track']['id'] for item in tracks]  # Collect track IDs

    # Get the audio features for the tracks
    audio_features = sp.audio_features(track_ids)

    # Analyze moods based on audio features
    for i, features in enumerate(audio_features):
        if features:
            track_name = tracks[i]['track']['name']
            valence = features['valence']  # Positivity measure
            energy = features['energy']  # Energy level
            mood = determine_mood(valence, energy)
            track_moods.append(mood)
            print(f"Track: {track_name}, Valence: {valence}, Energy: {energy}, Mood: {mood}")

    # Calculate the overall mood
    mood_count = Counter(track_moods)
    overall_mood = mood_count.most_common(1)[0][0] if mood_count else 'neutral'

    print(f"\nOverall Mood: {overall_mood}")

except spotipy.exceptions.SpotifyException as e:
    print(f"Error retrieving tracks: {e}")
