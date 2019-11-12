import datetime
import sqlite3


class DB(object):
    def __init__(self):
        self.conn = sqlite3.connect('venmo', check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = 1")
        self.create_transaction_table()
        self.create_user_table()
        self.create_join_table()

    def create_user_table(self):
        try:
            self.conn.execute("""
                CREATE TABLE user(
                    ID INTEGER PRIMARY KEY,
                    NAME TEXT NOT NULL,
                    USERNAME TEXT NOT NULL,
                    BALANCE FLOAT NOT NULL,
                    PASSWORD TEXT NOT NULL,
                    EMAIL TEXT NOT NULL
                );
            """)
        except Exception as e:
            print(e)

    def create_transaction_table(self):
        try:
            self.conn.execute("""
                CREATE TABLE transaction_table(
                    ID INTEGER PRIMARY KEY,
                    TIMESTAMP TEXT NOT NULL,
                    SENDER_ID INTEGER NOT NULL,
                    RECEIVER_ID INTEGER NOT NULL,
                    AMOUNT FLOAT NOT NULL,
                    MESSAGE TEXT NOT NULL,
                    ACCEPTED BOOL,
                    FOREIGN KEY (SENDER_ID) REFERENCES user(ID),
                    FOREIGN KEY (RECEIVER_ID) REFERENCES user(ID)
                );
            """)
        except Exception as e:
            print(e)

    def create_join_table(self):
        try:
            self.conn.execute("""
                CREATE TABLE friend_join(
                    ID INTEGER PRIMARY KEY,
                    USER_ID INTEGER NOT NULL,
                    FRIEND_ID INTEGER NOT NULL,
                    FOREIGN KEY (USER_ID) REFERENCES user(ID),
                    FOREIGN KEY (FRIEND_ID) REFERENCES user(ID)
                );
            """)
        except Exception as e:
            print(e)

    def create_friendship(self, user1_id, user2_id):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO friend_join (USER_ID, FRIEND_ID) VALUES (?, ?)', (user2_id, user1_id))
        cursor.execute('INSERT INTO friend_join (USER_ID, FRIEND_ID) VALUES (?, ?)', (user1_id, user2_id))
        self.conn.commit()
        return cursor.lastrowid

    def get_friends_of(self, user_id):
        cursor = self.conn.execute('SELECT * FROM friend_join WHERE USER_ID == ?', (user_id,))
        friends = []
        for row in cursor:
            friends.append(self.get_user_by_id(row[2]))
        return friends

    def get_all_users(self):
        cursor = self.conn.execute('SELECT * FROM user;')
        users = []
        for row in cursor:
            users.append({'id': row[0], 'name': row[1], 'username': row[2]})
        return users

    def insert_user(self, name, username, balance, password, email):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO user (NAME, USERNAME, BALANCE, PASSWORD, EMAIL) VALUES (?, ?, ?, ?, ?)', (name, username, balance, password, email))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_id(self, user_id):
        cursor = self.conn.execute('SELECT * FROM user WHERE ID == ?;', (user_id, ))
        for row in cursor:
            return {'id': row[0], 'name': row[1], 'username': row[2], 'balance': row[3], 'password': row[4], 'email': row[5], 'transactions': self.get_transactions_of_user(user_id)}
        return None

    def update_user_balances(self, sender_id, receiver_id, amount):
        sender_new_balance = self.get_user_by_id(sender_id)['balance'] - amount
        receiver_new_balance = self.get_user_by_id(receiver_id)['balance'] + amount
        cursor = self.conn.cursor()
        cursor.execute('UPDATE user SET BALANCE = ? WHERE ID == ?', (sender_new_balance, sender_id))
        cursor.execute('UPDATE user SET BALANCE = ? WHERE ID == ?', (receiver_new_balance, receiver_id))
        self.conn.commit()

    def delete_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM user WHERE ID == ?;', (user_id, ))
        self.conn.commit()

    def insert_transaction(self, timestamp, sender_id, receiver_id, amount, message, accepted):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO transaction_table (TIMESTAMP, SENDER_ID, RECEIVER_ID, AMOUNT, MESSAGE, ACCEPTED) VALUES (?, ?, ?, ?, ?, ?)', (timestamp, sender_id, receiver_id, amount, message, accepted))
        self.conn.commit()
        return cursor.lastrowid

    def get_transaction_by_id(self, transaction_id):
        cursor = self.conn.execute('SELECT * FROM transaction_table WHERE ID == ?;', (transaction_id, ))
        for row in cursor:
            accepted = bool(row[6]) if row[6] is not None else row[6]
            return {'id': row[0], 'timestamp': row[1], 'sender_id': row[2], 'receiver_id': row[3], 'amount': row[4], 'message': row[5], 'accepted': accepted}
        return None

    def get_transactions_of_user(self, user_id):
        cursor = self.conn.execute('SELECT * FROM transaction_table WHERE SENDER_ID = ? OR RECEIVER_ID = ?;', (user_id, user_id))
        transactions = []
        for row in cursor:
            accepted = bool(row[6]) if row[6] is not None else row[6]
            transactions.append({'id': row[0], 'timestamp': row[1], 'sender_id': row[2], 'receiver_id': row[3], 'amount': row[4], 'message': row[5], 'accepted': accepted})
        return transactions

    def update_transaction_accepted(self, transaction_id, accepted):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE transaction_table SET (TIMESTAMP, ACCEPTED) = (?, ?) WHERE ID == ?;', (datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), accepted, transaction_id))
        self.conn.commit()
        cursor.execute('SELECT * FROM transaction_table WHERE ID == ?;', (transaction_id,))
        for row in cursor:
            return {'id': row[0], 'timestamp': row[1], 'sender_id': row[2], 'receiver_id': row[3], 'amount': row[4], 'message': row[5], 'accepted': accepted}
        return None
