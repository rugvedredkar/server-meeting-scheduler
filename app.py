from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pathlib import Path
from pprint import pprint

from src.data import db
from src.auth import verify_token, require_auth

app = Flask(__name__)
CORS(app)

db_path = Path(__name__).parent/f"data/data.db"
db = db(db_path=db_path)

@app.route("/")
def index():
    return "hello from me"

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    pprint(data)
    token = data.get("id_token")

    if not token:
        return jsonify({"error": "Token missing"}), 400

    user = verify_token(token)
    pprint(user)
    if not user:
        return jsonify({"error": "Invalid token"}), 403

    user_id = db.get_user_by_email(user.get("email"))
    virgin = False

    # Adding user if doesnt exist
    if not user_id:
        db.create_user(user.get("sub"), user.get("name"), user.get("email"))
        virgin = True

    return jsonify({
        "message": "Login successful",
        "user": {
            "name": user.get("name"),
            "email": user.get("email"),
            "picture": user.get("picture")
        },
        "virgin" : virgin
    })

@app.route("/events")
@require_auth
def get_user_events():
    """Gets user events"""
    user_info = g.user
    google_sub = user_info.get("sub")
    user_name = db.get_user_name_by_id(google_sub)
    events = db.get_user_events(google_sub)

    pprint(events)

    events_list = []

    for event_id, _, title, desc, data, time, venue in events:

        events_list.append({
            'id': event_id,
            'title': title,
            'user': user_name,
            'description': desc,
            'date':data,
            'time':time,
            'venue':venue
        })
    
    return jsonify({
        "events" : events_list
    })

@app.route("/get_friends")
@require_auth
def get_user_friends():
    """Gets users friends"""
    # user_info = g.user
    # google_sub = user_info.get("sub")

    # friends = db.get_user_friends(google_sub)

    # return jsonify

@app.route("/add-friend-request")
def send_friends_request():
    """Adds a freinds request from current user to other user"""

    pass

@app.route("/search-users")
def search_users():
    """Takes a serach query and returns users related to that query"""

    pass

if __name__ == "__main__":

    app.run(port=8080, debug=True, host="0.0.0.0")