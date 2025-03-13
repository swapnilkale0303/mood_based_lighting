# server.py
from flask import Flask

app = Flask(__name__)

@app.route('/callback')
def callback():
    return "Authorization successful! You can close this window now."

if __name__ == '__main__':
    app.run(port=8888)
    
    
    
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import Counter

# Function to load credentials from a file
def load_credentials(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# Function to save credentials to a file
def save_credentials(filename, credentials):
    with open(filename, 'w') as file:
        json.dump(credentials, file)

# Create a data folder if it doesn't exist
data_folder = 'data'
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

# Get user credentials
client_id = input("Enter your Client ID: ")
client_secret = input("Enter your Client Secret: ")

# Define the path for the credentials file in the data folder
credentials_file = os.path.join(data_folder, 'spotify_credentials.json')

# Load existing credentials
credentials = load_credentials(credentials_file)

# Create a new SpotifyOAuth instance
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri='http://localhost:8888/callback',
                        scope='user-read-recently-played',
                        cache_path=credentials_file)

# If credentials exist and are valid, use them
if credentials:
    # Check if the token is expired and refresh it
    if 'expires_at' in credentials and sp_oauth.is_token_expired(credentials):
        print("Access token expired, refreshing...")
        token_info = sp_oauth.refresh_access_token(credentials['refresh_token'])
        credentials['access_token'] = token_info['access_token']
        credentials['refresh_token'] = token_info['refresh_token']
        credentials['expires_at'] = token_info['expires_at']
        save_credentials(credentials_file, credentials)
else:
    auth_url = sp_oauth.get_authorize_url()
    print(f"Please navigate to this URL to authorize: {auth_url}")
    input("Press Enter after you have authorized the app...")

    # Get the cached token
    token_info = sp_oauth.get_cached_token()

    # If token_info is None, it means you need to authorize again
    if not token_info:
        print("No valid token found. Please authorize the application.")
        exit()

    credentials = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": token_info['access_token'],
        "refresh_token": token_info['refresh_token'],
        "expires_at": token_info['expires_at']
    }
    save_credentials(credentials_file, credentials)

# Create a Spotify API client
sp = spotipy.Spotify(auth=credentials['access_token'])

# Get the user's recently played tracks
results = sp.current_user_recently_played(limit=10)
tracks = results['items']

# Display the track names and determine moods
track_moods = []

for item in tracks:
    track = item['track']
    track_name = track['name']
    track_artist = ', '.join(artist['name'] for artist in track['artists'])
    print(f"Track: {track_name} by {track_artist}")

    # Here you would implement mood detection logic; for now, we use placeholder moods.
    mood = "Neutral"  # Replace this with actual mood detection logic
    track_moods.append(mood)

# Calculate overall mood
mood_counter = Counter(track_moods)
overall_mood = mood_counter.most_common(1)[0][0]  # Get the most common mood

print(f"Overall Mood: {overall_mood}")
