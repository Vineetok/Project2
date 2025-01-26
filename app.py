from flask import Flask, render_template, redirect, url_for, request, session, flash
from pymongo import MongoClient
from bson import ObjectId


app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient('mongodb://localhost:27017/')
db = client['face_recognition']
users_collection = db['users']
reports_collection = db['reports']
requests_collection = db['registration_requests']

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username, 'password': password})

        if user:
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'superadmin':
                return redirect(url_for('approve_requests'))
            return redirect(url_for('report'))
        else:
            return render_template('login.html',error='Incorrect username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Save the registration request
        requests_collection.insert_one({'username': username, 'password': password, 'role': role})
        flash('Registration request sent to superadmin for approval')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/approve_requests')
def approve_requests():
    if 'username' not in session or session['role'] != 'superadmin':
        return redirect(url_for('login'))

    # Get all registration requests
    requests = list(requests_collection.find())
    return render_template('approve_requests.html', requests=requests)

@app.route('/approve/<request_id>', methods=['POST'])
def approve(request_id):
    if 'username' not in session or session['role'] != 'superadmin':
        return redirect(url_for('login'))

    # Approve the registration request
    request = requests_collection.find_one({'_id': ObjectId(request_id)})
    users_collection.insert_one({
        'username': request['username'],
        'password': request['password'],
        'role': request['role']
    })
    requests_collection.delete_one({'_id': ObjectId(request_id)})
    flash('User approved successfully')
    return redirect(url_for('approve_requests'))

@app.route('/reject/<request_id>', methods=['POST'])
def reject(request_id):
    if 'username' not in session or session['role'] != 'superadmin':
        return redirect(url_for('login'))

    # Reject the registration request
    requests_collection.delete_one({'_id': ObjectId(request_id)})
    flash('User rejected successfully')
    return redirect(url_for('approve_requests'))

@app.route('/report')
def report():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_role = session['role']

    # Filter reports based on user role
    if user_role == 'journalist':
        reports = reports_collection.find({'category': 'celebrities'}).sort('generated_at', -1)
    elif user_role == 'criminal':
        reports = reports_collection.find({'category': 'criminals'}).sort('generated_at', -1)
    elif user_role == 'sportsmen':
        reports = reports_collection.find({'category': 'sportsmen'}).sort('generated_at', -1)
    else:
        reports = []

    return render_template('report.html', reports=reports)

if __name__ == '__main__':
    app.run(debug=True)
