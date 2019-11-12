import datetime
import json
import os
import sqlite3

from flask import Flask, request
import db
from passlib.hash import sha256_crypt
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

Db = db.DB()
app = Flask(__name__)

def without_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}

@app.route('/api/users/')
def get_all_users():
    res = {'success': True, 'data': Db.get_all_users()}
    return json.dumps(res), 200

@app.route('/api/users/', methods=['POST'])
def create_user():
    post_body = json.loads(request.data)
    name = post_body['name']
    username = post_body['username']
    email = post_body['email']
    balance = post_body['balance']
    password = sha256_crypt.hash(post_body['password'])
    user_id = Db.insert_user(name, username, balance, password, email)
    user = {
        'id': user_id,
        'name': name,
        'username': username,
        'balance': balance,
        'email': email,
        'transactions': Db.get_transactions_of_user(user_id)
    }
    return json.dumps({'success': True, 'data': user}), 201

@app.route('/api/user/<int:user_id>/')
def get_user(user_id):
    user = Db.get_user_by_id(user_id)
    if not user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    body = json.loads(request.data)
    password = body['password']
    if not sha256_crypt.verify(password, user['password']):
        return json.dumps({'success': False, 'error': 'Incorrect password'}), 401
    return json.dumps({'success': True, 'data': without_keys(user, {'password'})}), 200

@app.route('/api/user/<int:user_id>/', methods=['DELETE'])
def delete_user(user_id):
    deleted_user = Db.get_user_by_id(user_id)
    if not deleted_user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    Db.delete_user(user_id)
    return json.dumps({'success': True, 'data': deleted_user}), 200

@app.route('/api/user/<int:user_id>/friends/')
def get_friends_of(user_id):
    friends = Db.get_friends_of(user_id)
    data = []
    for friend in friends:
        data.append(without_keys(friend, {'balance', 'password', 'email', 'transactions'}))
    res = {'success': True, 'data': data}
    return json.dumps(res), 200

@app.route('/api/user/<int:user_id>/friend/<int:friend_id>/', methods=['POST'])
def create_friendship(user_id, friend_id):
    try:
        friendship = {
            'id': Db.create_friendship(user_id, friend_id),
            'user_id': user_id,
            'friend_id': friend_id
        }
        return json.dumps({'success': True, 'data': friendship}), 201
    except sqlite3.IntegrityError:
        return json.dumps({'success': False, 'error': 'User not found'}), 404

@app.route('/api/transactions/', methods=['POST'])
def create_transaction():
    post_body = json.loads(request.data)
    sender_id = post_body['sender_id']
    receiver_id = post_body['receiver_id']
    sender = Db.get_user_by_id(sender_id)
    receiver = Db.get_user_by_id(receiver_id)
    amount = post_body['amount']
    message = post_body['message']
    accepted = post_body['accepted']
    sender_name = sender['name']
    timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    if amount > sender['balance']:
        return json.dumps({'success': False, 'error': 'Insufficient funds'}), 400

    transaction = {
        'id': Db.insert_transaction(timestamp, sender_id, receiver_id, amount, message, accepted),
        'timestamp': timestamp,
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'amount': amount,
        'message': message,
        'accepted': accepted
    }
    if accepted is None:
        subject = f'{sender_name} has requested ${amount} from you'
    else:
        Db.update_user_balances(sender_id, receiver_id, amount)
        subject = f'{sender_name} paid you ${amount}'
    message = Mail(
        from_email=sender['email'],
        to_emails=receiver['email'],
        subject=subject,
        html_content=message
    )
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print(str(e))
    return json.dumps({'success': True, 'data': transaction}), 201

@app.route('/api/transaction/<int:transaction_id>/', methods=['POST'])
def respond_to_transaction(transaction_id):
    transaction = Db.get_transaction_by_id(transaction_id)
    if not transaction:
        return json.dumps({'success': False, 'error': 'Transaction not found'}), 404
    if transaction['accepted'] is not None:
        return json.dumps({'success': False, 'error': 'Transaction already completed'}), 400
    accepted = json.loads(request.data)['accepted']
    if accepted is True:
        Db.update_user_balances(transaction['sender_id'], transaction['receiver_id'], transaction['amount'])
    transaction = Db.update_transaction_accepted(transaction_id, accepted)
    res = {'success': True, 'data': transaction}
    return json.dumps(res), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
