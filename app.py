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

# @app.route("/add-friend-request")
# def send_friends_request():
#     """Adds a freinds request from current user to other user"""

#     pass

# @app.route("/search-users")
# def search_users():
#     """Takes a serach query and returns users related to that query"""

#     pass

# added by rugved - 14 Apr
@app.route("/friends-availability")
@require_auth
def get_friends_availability():
    """Returns all user events (friend availability)"""
    user_info = g.user
    google_sub = user_info.get("sub")
    friends = db.get_user_friends(google_sub)

    all_availability = []
    for friend in friends:
        friend_id, name, email, *_ = friend
        events = db.get_user_events(friend_id)
        for event in events:
            event_id, _, _, _, date, time, _ = event
            all_availability.append({
                "id": event_id,
                "date": date,
                "time": time
            })

    pprint(all_availability)

    return jsonify(all_availability)


@app.route("/suggested-friends")
@require_auth
def suggested_friends():
    """Returns 5–6 friends of friends as suggested users"""
    user_info = g.user
    user_id = user_info.get("sub")

    direct_friends = db.get_user_friends(user_id)
    direct_ids = [f[0] for f in direct_friends]

    suggested = set()
    for fid in direct_ids:
        friends_of_friends = db.get_user_friends(fid)
        for fof in friends_of_friends:
            if fof[0] != user_id and fof[0] not in direct_ids:
                suggested.add((fof[0], fof[1], fof[2]))

    suggestions = list(suggested)[:6]
    result = [{"id": id, "name": name, "email": email} for id, name, email in suggestions]

    return jsonify(result)


@app.route("/search-users")
@require_auth
def search_users():
    """Search by name or email"""
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify([])

    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, email FROM users
            WHERE LOWER(username) LIKE ? OR LOWER(email) LIKE ?
        ''', (f"%{query}%", f"%{query}%"))
        users = cursor.fetchall()

    return jsonify([{"id": u[0], "name": u[1], "email": u[2]} for u in users])


@app.route("/friends")
@require_auth
def friends():
    """Get current user's friends"""
    user_info = g.user
    google_sub = user_info.get("sub")
    friends = db.get_user_friends(google_sub)

    return jsonify([{
        "id": f[0],
        "name": f[1],
        "email": f[2]
    } for f in friends])


@app.route("/friend-requests")
@require_auth
def pending_friend_requests():
    """Returns all pending friend requests for the user"""
    user_info = g.user
    user_id = user_info.get("sub")

    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.email
            FROM friend_requests fr
            JOIN users u ON fr.sender_id = u.id
            WHERE fr.receiver_id = ? AND fr.status = 'pending'
        ''', (user_id,))
        requests = cursor.fetchall()

    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in requests])


@app.route("/add-friend-request", methods=["POST"])
@require_auth
def send_friend_request():
    """Send friend request to a user"""
    data = request.get_json()
    receiver_id = data.get("receiver_id")
    sender_id = g.user.get("sub")

    if not receiver_id or receiver_id == sender_id:
        return jsonify({"error": "Invalid receiver"}), 400

    # Prevent duplicate
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM friend_requests
            WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
        ''', (sender_id, receiver_id))
        if cursor.fetchone():
            return jsonify({"error": "Friend request already sent"}), 400

    db.create_friend_request(sender_id, receiver_id)
    return jsonify({"message": "Friend request sent"}), 200


if __name__ == "__main__":

    app.run(port=8080, debug=True, host="0.0.0.0")


