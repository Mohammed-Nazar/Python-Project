from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = 'users.json'


class UserManager:
    @staticmethod
    def load_users():
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w') as f:
                json.dump({}, f)
        with open(USERS_FILE, 'r') as f:
            return json.load(f)

    @staticmethod
    def save_users(users):
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f)

    @staticmethod
    def add_user(username, password, is_admin=False):
        users = UserManager.load_users()
        if username in users:
            return False
        users[username] = {'password': password, 'balance': 0, 'is_admin': is_admin, 'transactions': []}
        UserManager.save_users(users)
        return True

    @staticmethod
    def delete_user(username):
        users = UserManager.load_users()
        if username in users:
            del users[username]
            UserManager.save_users(users)
            return True
        return False

    @staticmethod
    def get_all_transactions():
        users = UserManager.load_users()
        all_transactions = []
        for username, data in users.items():
            for transaction in data.get('transactions', []):
                transaction['user'] = username
                all_transactions.append(transaction)
        return all_transactions


class User:
    def __init__(self, username):
        self.username = username
        self.data = UserManager.load_users().get(username, {})
        if 'transactions' not in self.data:
            self.data['transactions'] = []

    def deposit(self, amount):
        self.data['balance'] += amount
        self.data['transactions'].append({'type': 'deposit', 'amount': amount, 'balance_after': self.data['balance']})
        self.save()

    def withdraw(self, amount):
        if self.data['balance'] >= amount:
            self.data['balance'] -= amount
            self.data['transactions'].append({'type': 'withdraw', 'amount': amount, 'balance_after': self.data['balance']})
            self.save()
            return True
        return False

    def transfer(self, recipient, amount):
        if self.withdraw(amount):
            recipient.deposit(amount)
            self.data['transactions'].append({'type': 'transfer', 'amount': amount, 'recipient': recipient.username, 'balance_after': self.data['balance']})
            recipient.data['transactions'].append({'type': 'received', 'amount': amount, 'sender': self.username, 'balance_after': recipient.data['balance']})
            self.save()
            recipient.save()
            return True
        return False

    def save(self):
        users = UserManager.load_users()
        users[self.username] = self.data
        UserManager.save_users(users)


# Routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = UserManager.load_users()
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['is_admin'] = users[username].get('is_admin', False)
            return redirect(url_for('user_dashboard')) if not session['is_admin'] else redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'username' not in session or session.get('is_admin', False):
        return redirect(url_for('login'))

    current_user = User(session['username'])

    if request.method == 'POST':
        action = request.form['action']
        amount = float(request.form['amount'])
        recipient_username = request.form.get('recipient')

        if action == 'deposit':
            current_user.deposit(amount)
            flash('Deposit successful', 'success')
        elif action == 'withdraw':
            if current_user.withdraw(amount):
                flash('Withdrawal successful', 'success')
            else:
                flash('Insufficient funds', 'danger')
        elif action == 'transfer':
            users = UserManager.load_users()
            if recipient_username in users:
                recipient = User(recipient_username)
                if current_user.transfer(recipient, amount):
                    flash('Transfer successful', 'success')
                else:
                    flash('Insufficient funds for transfer', 'danger')
            else:
                flash('Recipient does not exist', 'danger')

    return render_template('user_dashboard.html', user=current_user.data)


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or not session.get('is_admin', False):
        return redirect(url_for('login'))

    users = UserManager.load_users()
    all_transactions = UserManager.get_all_transactions()

    if request.method == 'POST':
        action = request.form['action']
        username = request.form['username']

        if action == 'delete':
            if UserManager.delete_user(username):
                flash(f'User {username} deleted successfully', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'User {username} not found', 'danger')
        elif action == 'add':
            password = request.form['password']
            is_admin = request.form.get('is_admin', False)
            if UserManager.add_user(username, password, is_admin):
                flash(f'User {username} added successfully', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'User {username} already exists', 'danger')

    return render_template('admin_dashboard.html', users=users, all_transactions=all_transactions)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)