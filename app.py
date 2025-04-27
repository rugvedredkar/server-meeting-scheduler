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
    return "hello from labhansh"

@app.route("/login", methods=["POST"])
def login():
    """Sends user info when user logs in ny verifying if the 
       user exists in google sessions"""
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

@app.route("/events", methods=["GET"])
@require_auth
def get_user_events():
    """Gets list of logged in user events"""
    user_info = g.user
    google_sub = user_info.get("sub")
    user_name = db.get_user_name_by_id(google_sub)

    events = db.get_user_events(google_sub)

    pprint(events)

    events_list = []

    for event_id, _, title, status, desc, date, time, venue in events:

        events_list.append({
            'id': event_id,
            'title': title,
            'meeting_status': status,
            'user': user_name,
            'description': desc,
            'date':date,
            'time':time,
            'venue':venue
        })
    
    return jsonify({
        "events" : events_list
    })

@app.route("/colleagues-availability", methods=["GET"])
@require_auth
def get_friends_availability():
    """Returns all user availability (friend availability)"""
    user_info = g.user
    google_sub = user_info.get("sub")

    all_availability = []

    friend_id = request.args.get('colleagues_id')
    pprint(friend_id)

    availability = db.get_user_events(friend_id)
    for event in availability:
        event_id, _, _, status, _, date, time, _ = event
        # if status == 'CONFIRMED':
        all_availability.append({
            "id": event_id,
            "date": date,
            "time": time
        })

    pprint(all_availability)
    return jsonify(all_availability)

@app.route("/friends", methods=["GET"])
@require_auth
def friends():
    """Get current user's friends"""
    user_info = g.user
    google_sub = user_info.get("sub")
    friends = db.get_user_friends(google_sub)

    pprint(friends)
    return jsonify([{
        "id": f[0],
        "name": f[1],
        "email": f[2]
    } for f in friends])

@app.route("/recents", methods=["GET"])
@require_auth
def recents():
    """Gets other users with whom the logged in user
       booked meetings with"""
    
    user_info = g.user
    google_sub = user_info.get("sub")

    events = db.get_user_events(google_sub);
    atendees_res = {}

    for event_id, _, _, _, _, _, _, _ in events:
        atendees = db.get_event_atendees(event_id)
        for atendee in atendees: 
            if atendee != google_sub:
                if atendee not in atendees_res:
                    atendees_res[atendee] = 1
                else:
                    atendees_res[atendee] += 1
    
    recents = []

    for attendee_id in atendees_res.keys():
        attendee = db.get_user_by_id(attendee_id)
        pprint(attendee)

        recents.append({
            "id": attendee[0],
            "name": attendee[1],
            "email": attendee[2]
        })

    return jsonify(recents)



@app.route("/suggested-friends")
@require_auth
def suggested_friends():
    """Returns quantity number of friends of friends as suggested users"""
    user_info = g.user
    user_id = user_info.get("sub")

    quantity = int(request.args.get("quantity", 6))

    direct_friends = db.get_user_friends(user_id)
    direct_ids = [f[0] for f in direct_friends]

    # Build set of suggested friends
    suggested = set()
    for fid in direct_ids:
        friends_of_friends = db.get_user_friends(fid)
        for fof in friends_of_friends:
            # Only add if not the user and not already a friend
            if fof[0] != user_id and fof[0] not in direct_ids:
                suggested.add((fof[0], fof[1], fof[2]))

    # Limit results to requested quantity
    suggestions = list(suggested)[:quantity]
    result = [{"id": id, "name": name, "email": email} for id, name, email in suggestions]

    return jsonify(result)

# ======= #

@app.route("/search-users", methods=["GET"])
@require_auth
def search_users():
    """Search by name or email"""
    query = request.args.get("query")
    pprint(query)
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


