from pathlib import Path
from src.data import db
import uuid
from datetime import datetime, timedelta
import random

# Initialize database
db_path = Path(__file__).parent / "data" / "data.db"
db = db(db_path=db_path)

user_data = [
    {'user_id': '116044433818751372016', 'email': 'labhanshtimande3@gmail.com', 'name': 'labhansh'},
    {'user_id': '112115853335709108858', 'email': 'labhanshtimande4@gmail.com', 'name': 'Labhansh Timande'},
    {'user_id': '113252154208412852558', 'email': 'rugvedredkar02@gmail.com', 'name': 'rugved redkar'},
    {'user_id': '115967835813635168125', 'email': 'redkarrugved02@gmail.com', 'name': 'Rugved Redkar'},
    {'user_id': '104560734505629189981', 'email': 'labhanshtimande2@gmail.com', 'name': 'Labhansh Timande'}
]

locations = ["Conference Room A", "Meeting Room B", "Virtual", "Cafeteria", "Office 101"]
event_titles = ["Team Meeting", "Project Review", "Sprint Planning", "Coffee Break", "Workshop"]
meeting_statuses = ["SENT", "CONFIRMED", "CANCELED"]
request_statuses = ["REQUESTED", "ACCEPTED", "REJECTED"]

def get_random_picture():
    # Returns a random image from picsum.photos
    random_id = random.randint(1, 1000)
    return f"https://picsum.photos/id/{random_id}/200/200"

# Create users
users = []
for user in user_data:
    if user['user_id'] and user['email'] and user['name']:
        try:
            # Slight change: insert with picture now
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (id, username, email, provider, picture)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user['user_id'], user['name'], user['email'], 'google', get_random_picture()))
                conn.commit()

            users.append(user['user_id'])
            print(f"Created user: {user['name']}")
        except Exception as e:
            print(f"Error creating user {user['name']}: {e}")

# Create friendships
for i in range(len(users)):
    sender = users[i]
    possible_receivers = [u for idx, u in enumerate(users) if idx != i]
    selected_receivers = random.sample(possible_receivers, k=random.randint(1, min(3, len(possible_receivers))))
    
    for receiver in selected_receivers:
        try:
            request_id = db.create_friend_request(sender, receiver)
            print(f"Created friend request from {sender} to {receiver} (request ID: {request_id})")

            friendship_id = db.create_friendship(sender, receiver)
            print(f"Created friendship between {sender} and {receiver} (friendship ID: {friendship_id})")
        except Exception as e:
            print(f"Error creating friendship: {e}")

# Create events
start_date = datetime.now()
for user_id in users:
    for _ in range(3):  # Create 3 events per user
        title = random.choice(event_titles)
        description = f"Description for {title}"
        event_date = (start_date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        event_time = f"{random.randint(9, 17):02d}:00"
        location = random.choice(locations)
        meeting_status = random.choice(meeting_statuses)
        
        try:
            event_id = str(uuid.uuid4())
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (id, user_id, title, meeting_status, description, date, time, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (event_id, user_id, title, meeting_status, description, event_date, event_time, location))
                conn.commit()
            print(f"Created event: {title} with meeting status {meeting_status}")

            # Add attendees
            attendees = random.sample(users, random.randint(2, min(5, len(users))))
            for attendee_id in attendees:
                try:
                    attendee_uuid = str(uuid.uuid4())
                    request_status = random.choice(request_statuses)
                    with db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO event_attendees (id, event_id, user_id, request_status)
                            VALUES (?, ?, ?, ?)
                        ''', (attendee_uuid, event_id, attendee_id, request_status))
                        conn.commit()
                    print(f"Added attendee {attendee_id} to event {title} with request status {request_status}")
                except Exception as e:
                    print(f"Error adding attendee: {e}")

        except Exception as e:
            print(f"Error creating event: {e}")

print("Database population completed!")
