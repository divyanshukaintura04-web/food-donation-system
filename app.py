import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "food_donation.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "replace_with_a_random_secret"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    sql_file = os.path.join(BASE_DIR, "database", "schema.sql")
    conn = sqlite3.connect(DB_PATH)
    with open(sql_file, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    cur = conn.cursor()
    cur.execute("SELECT * FROM Admin WHERE Username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute("INSERT INTO Admin (Username, Password, Role) VALUES (?, ?, ?)",
                    ("admin", generate_password_hash("admin123"), "SuperAdmin"))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        usertype = request.form['usertype']
        name = request.form['name']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        proof_type = request.form.get('proof_type')
        proof_number = request.form.get('proof_number')
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO User (UserType, Name, ContactNumber, Email, Address, ProofType, ProofNumber, Username, Password) VALUES (?,?,?,?,?,?,?,?,?)',
                         (usertype, name, contact, email, address, proof_type, proof_number, username, password))
            conn.commit()
            flash("Account created. Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "danger")
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role', 'user')
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        if role == 'admin':
            admin = conn.execute('SELECT * FROM Admin WHERE Username = ?', (username,)).fetchone()
            conn.close()
            if admin and check_password_hash(admin['Password'], password):
                session['admin_id'] = admin['AdminID']
                session['admin_username'] = admin['Username']
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials', 'danger')
                return redirect(url_for('login'))
        else:
            user = conn.execute('SELECT * FROM User WHERE Username = ?', (username,)).fetchone()
            conn.close()
            if user and check_password_hash(user['Password'], password):
                session['user_id'] = user['UserID']
                session['user_type'] = user['UserType']
                session['username'] = user['Name']
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/user/dashboard')
def user_dashboard():
    conn = get_db_connection()
    food = conn.execute("SELECT f.*, d.Name as DonorName, d.Address as DonorAddress FROM FoodItem f LEFT JOIN Donor d ON f.DonorID=d.DonorID WHERE f.Status='Available' ORDER BY f.FoodID DESC").fetchall()
    conn.close()
    return render_template('user_dashboard.html', food=food)

@app.route('/request/new/<int:food_id>', methods=['GET','POST'])
def new_request(food_id):
    if 'user_id' not in session:
        flash("Please login to request", "warning")
        return redirect(url_for('login'))
    conn = get_db_connection()
    food = conn.execute('SELECT * FROM FoodItem WHERE FoodID=?', (food_id,)).fetchone()
    if request.method == 'POST':
        proof = request.files.get('proof')
        filename = None
        if proof:
            filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{proof.filename}")
            proof.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn.execute('INSERT INTO Request (UserID, FoodID, ProofFile, RequestDate, Status, Verified) VALUES (?,?,?,?,?,?)',
                     (session['user_id'], food_id, filename, datetime.utcnow().isoformat(), 'Pending', 'No'))
        conn.commit()
        conn.close()
        flash('Request submitted. Waiting for admin approval.', 'info')
        return redirect(url_for('user_dashboard'))
    conn.close()
    return render_template('request_form.html', food=food)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    requests = conn.execute('SELECT r.*, u.Name as Requester, f.FoodName, d.Name as DonorName FROM Request r LEFT JOIN User u ON r.UserID=u.UserID LEFT JOIN FoodItem f ON r.FoodID=f.FoodID LEFT JOIN Donor d ON f.DonorID=d.DonorID ORDER BY r.RequestDate DESC').fetchall()
    volunteers = conn.execute('SELECT * FROM Volunteer').fetchall()
    users = conn.execute('SELECT * FROM User').fetchall()
    donors = conn.execute('SELECT * FROM Donor').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', requests=requests, volunteers=volunteers, users=users, donors=donors)

@app.route('/admin/approve/<int:reqid>', methods=['POST'])
def admin_approve(reqid):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    action = request.form.get('action')
    conn = get_db_connection()
    if action == 'approve':
        conn.execute("UPDATE Request SET Status='Approved', Verified='Yes' WHERE ReqID=?", (reqid,))
        conn.commit()
        flash("Request approved. Assign a volunteer.", "success")
    elif action == 'reject':
        conn.execute("UPDATE Request SET Status='Rejected' WHERE ReqID=?", (reqid,))
        conn.commit()
        flash("Request rejected.", "warning")
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_volunteer', methods=['POST'])
def admin_assign_volunteer():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    reqid = request.form.get('reqid')
    volid = request.form.get('volid')
    conn = get_db_connection()
    conn.execute('INSERT INTO Delivery (ReqID, VolID, PickupTime, Status) VALUES (?,?,?,?)', (reqid, volid, datetime.utcnow().isoformat(), 'Picked'))
    conn.execute('UPDATE Request SET Status="Assigned" WHERE ReqID=?', (reqid,))
    req = conn.execute('SELECT * FROM Request WHERE ReqID=?', (reqid,)).fetchone()
    if req and req['FoodID']:
        conn.execute('UPDATE FoodItem SET Status="Assigned" WHERE FoodID=?', (req['FoodID'],))
    conn.commit()
    conn.close()
    flash("Volunteer assigned and delivery created.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_volunteer', methods=['POST'])
def admin_add_volunteer():
    if 'admin_id' not in session():
        return redirect(url_for('login'))
    name = request.form['name']
    contact = request.form['contact']
    ngoid = request.form.get('ngoid')
    conn = get_db_connection()
    conn.execute('INSERT INTO Volunteer (Name, ContactNumber, NGOID) VALUES (?,?,?)', (name, contact, ngoid))
    conn.commit()
    conn.close()
    flash('Volunteer added.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/volunteer/dashboard')
def volunteer_dashboard():
    conn = get_db_connection()
    deliveries = conn.execute('SELECT del.*, r.Status as ReqStatus, r.ProofFile, u.Name as RequesterName FROM Delivery del LEFT JOIN Request r ON del.ReqID=r.ReqID LEFT JOIN User u ON r.UserID=u.UserID ORDER BY del.PickupTime DESC').fetchall()
    conn.close()
    return render_template('volunteer_dashboard.html', deliveries=deliveries)

@app.route('/volunteer/update/<int:delivery_id>', methods=['POST'])
def volunteer_update(delivery_id):
    status = request.form['status']
    conn = get_db_connection()
    if status == 'Delivered':
        conn.execute("UPDATE Delivery SET Status='Delivered', DeliveryTime=? WHERE DeliveryID=?", (datetime.utcnow().isoformat(), delivery_id))
        delivery = conn.execute("SELECT * FROM Delivery WHERE DeliveryID=?", (delivery_id,)).fetchone()
        if delivery:
            conn.execute("UPDATE Request SET Status='Delivered' WHERE ReqID=?", (delivery['ReqID'],))
    else:
        conn.execute("UPDATE Delivery SET Status=? WHERE DeliveryID=?", (status, delivery_id))
    conn.commit()
    conn.close()
    flash("Delivery status updated.", "success")
    return redirect(url_for('volunteer_dashboard'))

@app.route('/feedback/<int:donorid>', methods=['GET','POST'])
def feedback(donorid):
    if request.method == 'POST':
        user_id = session.get('user_id')
        rating = int(request.form['rating'])
        comments = request.form['comments']
        conn = get_db_connection()
        conn.execute("INSERT INTO Feedback (UserID, DonorID, Rating, Comments, Date) VALUES (?,?,?,?,?)", (user_id, donorid, rating, comments, datetime.utcnow().date().isoformat()))
        conn.commit()
        conn.close()
        flash("Feedback submitted. Thank you!", "success")
        return redirect(url_for('user_dashboard'))
    return render_template('feedback.html', donorid=donorid)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
