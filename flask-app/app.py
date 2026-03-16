from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

users = {}  # replace with a real database later

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Please enter email and password.'}), 400
    if email not in users or users[email] != password:
        return jsonify({'error': 'Invalid email or password.'}), 401

    return jsonify({'success': True, 'message': 'Login successful!'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Fill all fields'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password too short (min 6 chars)'}), 400
    if email in users:
        return jsonify({'error': 'Email already registered'}), 400

    users[email] = password
    return jsonify({'success': True, 'message': 'Registered! Go to login'})

if __name__ == '__main__':
    import os
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
