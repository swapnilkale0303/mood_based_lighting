import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os
from collections import Counter
from flask import Flask, request, redirect, url_for, render_template

app = Flask(__name__)

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

# Function to determine mood based on track's audio features
def determine_mood(valence, energy):
    if valence > 0.6:
        return 'happy' if energy > 0.7 else 'calm'
    elif valence < 0.4:
        return 'angry' if energy > 0.7 else 'sad'
    else:
        return 'neutral'

@app.route('/')
def index():
    return render_template('index.html')  # Changed back to index.html

@app.route('/login', methods=['GET'])
def login():
    username = request.args.get('username')
    credentials_file = f'{username}_spotify_credentials.json'

    credentials = load_credentials(credentials_file)

    sp_oauth = SpotifyOAuth(
        client_id=credentials['client_id'] if credentials else request.args.get('client_id'),
        client_secret=credentials['client_secret'] if credentials else request.args.get('client_secret'),
        redirect_uri='http://localhost:8888/callback',  # Hardcoded to match your redirect URI
        scope='user-read-recently-played user-read-playback-state',
        cache_path=credentials_file
    )

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    else:
        return redirect(url_for('callback', token=token_info['access_token']))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    sp_oauth = SpotifyOAuth(redirect_uri='http://localhost:8888/callback')  # Hardcoded to match your redirect URI
    token_info = sp_oauth.get_access_token(code)

    # Save credentials
    credentials = {
        'client_id': sp_oauth.client_id,
        'client_secret': sp_oauth.client_secret,
        'access_token': token_info['access_token'],
        'refresh_token': token_info.get('refresh_token')
    }
    username = request.args.get('username')
    credentials_file = f'{username}_spotify_credentials.json'
    save_credentials(credentials_file, credentials)

    return redirect(url_for('mood', username=username))  # Pass username to mood route

@app.route('/mood')
def mood():
    username = request.args.get('username')
    credentials_file = f'{username}_spotify_credentials.json'
    credentials = load_credentials(credentials_file)

    sp = spotipy.Spotify(auth=credentials['access_token'])

    try:
        results = sp.current_user_recently_played(limit=10)
        tracks = results['items']
        
        track_moods = []
        track_ids = [item['track']['id'] for item in tracks]  

        audio_features = sp.audio_features(track_ids)

        for i, features in enumerate(audio_features):
            if features:
                valence = features['valence']
                energy = features['energy']
                mood = determine_mood(valence, energy)
                track_moods.append(mood)

        mood_count = Counter(track_moods)
        overall_mood = mood_count.most_common(1)[0][0] if mood_count else 'neutral'

        return f"Overall Mood: {overall_mood}"

    except spotipy.exceptions.SpotifyException as e:
        return f"Error retrieving tracks: {e}"

if __name__ == '__main__':
    app.run(port=8888, debug=True)  # Ensure the correct port is specified
