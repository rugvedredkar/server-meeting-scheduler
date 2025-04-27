from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pathlib import Path
from pprint import pprint
import uuid

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
        db.create_user(user.get("sub"), user.get("name"), user.get("email"), user.get("picture"))
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

@app.route("/user-info", methods=["GET"])
@require_auth
def get_user_info():
    """Gets user info by user ID"""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, picture
                FROM users
                WHERE id = ?
            ''', (user_id,))
            user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user_info = {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "picture": user[3]
        }

        return jsonify(user_info), 200

    except Exception as e:
        print(f"Error fetching user info: {e}")
        return jsonify({"error": "Internal server error"}), 500


"""=========EVENTS APIS=========="""
@app.route("/events", methods=["GET"])
@require_auth
def get_user_events():
    """Gets list of logged-in user's events including attendees (excluding self)."""
    user_info = g.user
    google_sub = user_info.get("sub")
    user_name = db.get_user_name_by_id(google_sub)

    events = db.get_user_events(google_sub)

    events_list = []

    for event_id, _, title, status, desc, date, time, venue in events:
        # Get attendees for this event
        attendees = db.get_event_atendees(event_id)
        attendees = [attendee for attendee in attendees if attendee != google_sub]

        events_list.append({
            'id': event_id,
            'title': title,
            'meeting_status': status,
            'user': user_name,
            'description': desc,
            'date': date,
            'time': time,
            'venue': venue,
            'attendees': attendees
        })

    return jsonify({
        "events": events_list
    })


@app.route("/create-event", methods=["POST"])
@require_auth
def create_event():
    """Creates a new event and adds attendees with default request status 'REQUESTED'."""
    user_info = g.user
    google_sub = user_info.get("sub")

    data = request.get_json()

    title = data.get('title')
    meeting_status = data.get('meeting_status', 'SENT')
    description = data.get('description')
    date = data.get('date')
    time_ = data.get('time')
    location = data.get('venue')
    attendees = data.get('attendees', [])

    if not title or not date or not time_ or not location:
        return jsonify({"error": "Missing required event fields"}), 400

    try:
        event_id = str(uuid.uuid4())
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (id, user_id, title, meeting_status, description, date, time, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (event_id, google_sub, title, meeting_status, description, date, time_, location))
            conn.commit()

        for attendee_id in attendees:
            attendee_uuid = str(uuid.uuid4())
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO event_attendees (id, event_id, user_id, request_status)
                    VALUES (?, ?, ?, ?)
                ''', (attendee_uuid, event_id, attendee_id, 'REQUESTED'))
                conn.commit()

        return jsonify({
            "message": "Event created successfully",
            "event_id": event_id
        }), 201

    except Exception as e:
        print(f"Error creating event: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/event-requests", methods=["GET"])
@require_auth
def get_pending_or_rejected_events():
    """Gets list of events where the logged-in user is an attendee with REQUESTED or REJECTED status, including attendees list."""
    user_info = g.user
    google_sub = user_info.get("sub")

    event_ids = db.get_pending_or_rejected_events_for_user(google_sub)

    events_list = []

    for event_id in event_ids:
        event = db.get_event_by_id(event_id)
        if event:
            eid, owner_id, title, meeting_status, desc, date, time, venue = event

            # Get event owner's name
            owner_name = db.get_user_name_by_id(owner_id)

            # Get attendees for this event (excluding self)
            attendees = db.get_event_atendees(eid)
            attendees = [attendee for attendee in attendees if attendee != google_sub]

            if owner_id != google_sub:
                events_list.append({
                    'id': eid,
                    'title': title,
                    'meeting_status': meeting_status,
                    'user': owner_name,
                    'description': desc,
                    'date': date,
                    'time': time,
                    'venue': venue,
                    'attendees': attendees
                })

    return jsonify({
        "events": events_list
    })

"""=========EVENTS ACTIONS=========="""
@app.route("/event-attendees", methods=["GET"])
@require_auth
def get_event_attendee_status():
    """Returns list of attendees and their request status for a specific event."""
    user_info = g.user
    google_sub = user_info.get("sub")

    event_id = request.args.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, request_status FROM event_attendees
                WHERE event_id = ?
            ''', (event_id,))
            attendees = cursor.fetchall()

        attendee_list = []
        for user_id, status in attendees:
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, picture
                    FROM users
                    WHERE id = ?
                ''', (user_id,))
                user = cursor.fetchone()

            if user and user_id != google_sub:
                attendee_list.append({
                    "user_id": user_id,
                    "status": status,
                    "user": {
                        "id": user[0],
                        "name": user[1],
                        "email": user[2],
                        "picture": user[3]
                    }
                })

        return jsonify({"attendees": attendee_list}), 200

    except Exception as e:
        print(f"Error fetching event attendees: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/accept-event", methods=["POST"])
@require_auth
def accept_event():
    """Accepts an event invitation for an attendee."""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE event_attendees
                SET request_status = 'ACCEPTED'
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, google_sub))
            conn.commit()

        return jsonify({"message": "Event accepted"}), 200

    except Exception as e:
        print(f"Error accepting event: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/reject-event", methods=["POST"])
@require_auth
def reject_event():
    """Rejects an event invitation for an attendee."""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE event_attendees
                SET request_status = 'REJECTED'
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, google_sub))
            conn.commit()

        return jsonify({"message": "Event rejected"}), 200

    except Exception as e:
        print(f"Error rejecting event: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/confirm-event", methods=["POST"])
@require_auth
def confirm_event():
    """Confirms (sends out) an event by the creator."""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            # Make sure only creator can confirm
            cursor.execute('''
                UPDATE events
                SET meeting_status = 'CONFIRMED'
                WHERE id = ? AND user_id = ?
            ''', (event_id, google_sub))
            conn.commit()

        return jsonify({"message": "Event confirmed"}), 200

    except Exception as e:
        print(f"Error confirming event: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/cancel-event", methods=["POST"])
@require_auth
def cancel_event():
    """Cancels an event by the creator."""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            # Make sure only creator can cancel
            cursor.execute('''
                UPDATE events
                SET meeting_status = 'CANCELED'
                WHERE id = ? AND user_id = ?
            ''', (event_id, google_sub))
            conn.commit()

        return jsonify({"message": "Event canceled"}), 200

    except Exception as e:
        print(f"Error canceling event: {e}")
        return jsonify({"error": "Internal server error"}), 500


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

"""=========FRIENDS APIS=============="""
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

@app.route("/search-users", methods=["GET"])
@require_auth
def search_users():
    """Search by name or email"""
    user_info = g.user
    user_id = user_info.get("sub")

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

@app.route("/friend-requests", methods=["GET"])
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

@app.route("/remove-friend", methods=["DELETE"])
@require_auth
def remove_friend():
    """Removes a friendship between two users"""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    friend_id = data.get("friend_id")
    if not friend_id:
        return jsonify({"error": "friend_id is required"}), 400

    try:
        db.remove_friendship(google_sub, friend_id)
        return jsonify({"message": "Friend removed"}), 200
    except Exception as e:
        print(f"Error removing friend: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/cancel-friend-request", methods=["DELETE"])
@require_auth
def cancel_friend_request():
    """Cancels a pending friend request that the user sent"""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    receiver_id = data.get("receiver_id")
    if not receiver_id:
        return jsonify({"error": "receiver_id is required"}), 400

    try:
        db.cancel_friend_request(google_sub, receiver_id)
        return jsonify({"message": "Friend request canceled"}), 200
    except Exception as e:
        print(f"Error cancelling friend request: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/accept-friend-request", methods=["POST"])
@require_auth
def accept_friend_request():
    """Accepts a received friend request"""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    sender_id = data.get("sender_id")
    if not sender_id:
        return jsonify({"error": "sender_id is required"}), 400

    try:
        db.accept_friend_request(sender_id, google_sub)
        return jsonify({"message": "Friend request accepted"}), 200
    except Exception as e:
        print(f"Error accepting friend request: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/reject-friend-request", methods=["DELETE"])
@require_auth
def reject_friend_request():
    """Rejects a received friend request"""
    user_info = g.user
    google_sub = user_info.get("sub")
    data = request.get_json()

    sender_id = data.get("sender_id")
    if not sender_id:
        return jsonify({"error": "sender_id is required"}), 400

    try:
        db.reject_friend_request(sender_id, google_sub)
        return jsonify({"message": "Friend request rejected"}), 200
    except Exception as e:
        print(f"Error rejecting friend request: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route("/friend-status", methods=["GET"])
@require_auth
def get_friend_status():
    """Gets the relationship status between current user and another user"""
    user_info = g.user
    google_sub = user_info.get("sub")
    
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required as query parameter"}), 400

    try:
        # Check if they are already friends
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM friendships
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            ''', (google_sub, user_id, user_id, google_sub))
            friendship = cursor.fetchone()
        
        if friendship:
            return jsonify({"status": "friend"}), 200

        # Check if current user has sent a friend request
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM friend_requests
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            ''', (google_sub, user_id))
            sent_request = cursor.fetchone()
        
        if sent_request:
            return jsonify({"status": "request_sent"}), 200

        # Check if the other user has sent a friend request
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM friend_requests
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            ''', (user_id, google_sub))
            received_request = cursor.fetchone()
        
        if received_request:
            return jsonify({"status": "request_received"}), 200

        # If none of the above, return "none"
        return jsonify({"status": "none"}), 200

    except Exception as e:
        print(f"Error checking friend status: {e}")
        return jsonify({"error": "Internal server error"}), 500



if __name__ == "__main__":

    app.run(port=8080, debug=True, host="0.0.0.0")


