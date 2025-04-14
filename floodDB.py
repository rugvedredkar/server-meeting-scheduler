from pathlib import Path
from src.data import db
import uuid
from datetime import datetime, timedelta
import random

# Initialize database
db_path = Path(__name__).parent/f"data/data.db"
db = db(db_path=db_path)

user_data = [

    {
        'user_id': '116044433818751372016',
        'email':'labhanshtimande3@gmail.com',
        'name':'labhansh'
    },
    {
        'user_id': '112115853335709108858',
        'email':'labhanshtimande4@gmail.com',
        'name':'Labhansh Timande'
    },
    {
        'user_id': '113252154208412852558',
        'email':'rugvedredkar02@gmail.com',
        'name':'rugved redkar'
    },
    {
        'user_id': '115967835813635168125',
        'email':'redkarrugved02@gmail.com',
        'name':'Rugved Redkar'
    }
]

# Sample data
locations = ["Conference Room A", "Meeting Room B", "Virtual", "Cafeteria", "Office 101"]
event_titles = ["Team Meeting", "Project Review", "Sprint Planning", "Coffee Break", "Workshop"]

# Create users from user_data
users = []
for user in user_data:
    if user['user_id'] and user['email'] and user['name']:  # Only create users with valid data
        try:
            db.create_user(user['user_id'], user['name'], user['email'], provider='google')
            users.append(user['user_id'])
            print(f"Created user: {user['name']}")
        except Exception as e:
            print(f"Error creating user {user['name']}: {e}")

# Create friendships between all valid users
for i in range(len(users)):
    for j in range(i + 1, len(users)):
        try:
            # Create friend request
            request_id = db.create_friend_request(users[i], users[j])
            print(f"Created friend request between {users[i]} and {users[j]}")
            
            # Create friendship
            friendship_id = db.create_friendship(users[i], users[j])
            print(f"Created friendship between {users[i]} and {users[j]}")
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
        
        try:
            event_id = db.create_event(user_id, title, description, event_date, event_time, location)
            print(f"Created event: {title}")
            
            # Add random attendees
            attendees = random.sample(users, random.randint(2, 5))
            for attendee_id in attendees:
                try:
                    db.add_event_attendee(event_id, attendee_id)
                    print(f"Added attendee to event {title}")
                except Exception as e:
                    print(f"Error adding attendee: {e}")
                    
        except Exception as e:
            print(f"Error creating event: {e}")

print("Database population completed!")

