import sqlite3
from datetime import datetime
import uuid

class db:
    def __init__(self, db_path='meetings.db'):
        self.db_path = db_path
        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                picture TEXT NOT NULL,
                provider TEXT NOT NULL,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS friend_requests (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                status TEXT NOT NULL,
                sentAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                id TEXT PRIMARY KEY,
                user1_id TEXT NOT NULL,
                user2_id TEXT NOT NULL,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id)
            )''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                meeting_status TEXT NOT NULL,
                description TEXT,
                date TEXT,
                time TEXT,
                location TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_attendees (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                request_status TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')

            conn.commit()

    ### =========== USER ========== ####
    def create_user(self, user_id, username, email, picture, provider='google'):
        with self.connect() as conn:
            cursor = conn.cursor()
            # user_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO users (id, username, email, picture, provider)
            VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, email, picture, provider))
            conn.commit()
            return user_id
        
    def get_user_by_id(self, user_id):

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            return result if result else False

    def get_user_name_by_id(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else False
        
    def get_user_by_email(self, email):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            return cursor.fetchone() or False

    ### ======= FRIENDSHIPS ========= ###
    def get_user_friends(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT u.* FROM users u
            INNER JOIN friendships f ON (f.user1_id = u.id OR f.user2_id = u.id)
            WHERE (f.user1_id = ? OR f.user2_id = ?) AND u.id != ?
            ''', (user_id, user_id, user_id))
            return cursor.fetchall()
        
    def create_friend_request(self, sender_id, receiver_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            request_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO friend_requests (id, sender_id, receiver_id, status)
            VALUES (?, ?, ?, ?)
            ''', (request_id, sender_id, receiver_id, 'pending'))
            conn.commit()
            return request_id

    def create_friendship(self, user1_id, user2_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            friendship_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO friendships (id, user1_id, user2_id)
            VALUES (?, ?, ?)
            ''', (friendship_id, user1_id, user2_id))
            conn.commit()
            return friendship_id

    def remove_friendship(self, user1_id, user2_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM friendships
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            ''', (user1_id, user2_id, user2_id, user1_id))
            conn.commit()

    def cancel_friend_request(self, sender_id, receiver_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM friend_requests
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            ''', (sender_id, receiver_id))
            conn.commit()

    def accept_friend_request(self, sender_id, receiver_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            # Update friend request status
            cursor.execute('''
                UPDATE friend_requests
                SET status = 'accepted'
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            ''', (sender_id, receiver_id))

            # Create a friendship
            friendship_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO friendships (id, user1_id, user2_id)
                VALUES (?, ?, ?)
            ''', (friendship_id, sender_id, receiver_id))

            conn.commit()
            return friendship_id

    def reject_friend_request(self, sender_id, receiver_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE friend_requests
                SET status = 'rejected'
                WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            ''', (sender_id, receiver_id))
            conn.commit()


    ### ========== EVENTS ========= ###
    def get_user_events(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE user_id = ?', (user_id,))
            return cursor.fetchall()
    
    def get_event_by_id(self, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            result = cursor.fetchone()
            return result if result else False
    
    def create_event(self, user_id, title, description, date, time, location):
        with self.connect() as conn:
            cursor = conn.cursor()
            event_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO events (id, user_id, title, description, date, time, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (event_id, user_id, title, description, date, time, location))
            conn.commit()
            return event_id
        
    def get_pending_or_rejected_events_for_user(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT event_id FROM event_attendees
                WHERE user_id = ?
                AND (request_status = 'REQUESTED' OR request_status = 'REJECTED')
            ''', (user_id,))
            return [row[0] for row in cursor.fetchall()]

    ## EVENT ATENDEES ## 
    def get_event_atendees(self, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM event_attendees WHERE event_id = ?', (event_id,))
            return [row[0] for row in cursor.fetchall()]

    def add_event_attendee(self, event_id, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            attendee_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO event_attendees (id, event_id, user_id)
            VALUES (?, ?, ?)
            ''', (attendee_id, event_id, user_id))
            conn.commit()
            return attendee_id
        

if __name__ == "__main__":

    # db_path = Path(__name__).parent.parent/f"data/data.db"
    # db = db(db_path=db_path)

    # db.create_event('116044433818751372016', 'some event')

    ...
