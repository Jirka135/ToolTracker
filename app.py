from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import cv2
from pyzbar.pyzbar import decode
import random
import string
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import sqlite3
import zipfile
from io import BytesIO
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

LOG_FILE_PATH = 'instance/app.log'

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    qr_code = db.Column(db.String(120), unique=True, nullable=False)
    location = db.Column(db.String(120), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    return_date = db.Column(db.DateTime, nullable=True)

class ToolLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'borrowed', 'returned', 'maintenance'
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    details = db.Column(db.Text, nullable=True)
    
    tool = db.relationship('Tool', backref=db.backref('logs', lazy=True))
    user = db.relationship('User', backref=db.backref('logs', lazy=True))
    
    tool = db.relationship('Tool', backref=db.backref('logs', lazy=True))
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

with app.app_context():
    db.create_all()

def log_tool_action(tool_id, user_id, action, details=None):
    log_entry = ToolLog(tool_id=tool_id, user_id=user_id, action=action, details=details, timestamp=datetime.datetime.now(datetime.timezone.utc))
    db.session.add(log_entry)
    db.session.commit()

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def backup_database():
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f'database_backup_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.db')
    conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    with open(backup_file, 'wb') as f:
        for line in conn.iterdump():
            f.write(f'{line}\n'.encode('utf-8'))
    print(f"Backup created at {backup_file}")

def restore_database(backup_file):
    conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    cursor = conn.cursor()
    with open(backup_file, 'r') as f:
        sql = f.read()
        cursor.executescript(sql)
    conn.commit()
    print(f"Database restored from {backup_file}")

def generate_qr_code(tool):
    security_token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    qr_data = f"{tool.id}:{tool.name}:{security_token}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    qr_code_dir = os.path.join('static', 'qr_codes')
    os.makedirs(qr_code_dir, exist_ok=True)
    
    qr_code_filename = f"{tool.name}_{tool.id}_{tool.location.replace(' ', '_')}_QRcode.png"
    qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
    
    img.save(qr_code_path)
    return qr_code_path

def add_tool(name, location):
    new_tool = Tool(name=name, location=location, qr_code="placeholder")
    db.session.add(new_tool)
    db.session.commit()
    
    qr_code = generate_qr_code(new_tool)
    new_tool.qr_code = qr_code
    db.session.commit()
    print(f"Tool '{name}' added with QR code.")

def remove_tool(tool_id):
    tool = db.session.get(Tool, tool_id)
    if tool:
        db.session.delete(tool)
        db.session.commit()
        print(f"Tool ID '{tool_id}' removed.")
    else:
        print(f"Tool ID '{tool_id}' not found.")

def list_tools():
    tools = Tool.query.all()
    for tool in tools:
        print(f"Tool ID: {tool.id}, Name: {tool.name}, Location: {tool.location}, QR Code: {tool.qr_code}")

def identify_tool_from_qr_code(file_path):
    img = cv2.imread(file_path)
    decoded_objects = decode(img)
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        tool_id = qr_data.split(':')[0]
        tool = db.session.get(Tool, tool_id)
        if tool:
            print(f"QR code corresponds to Tool ID: {tool.id}, Name: {tool.name}")
            return tool
    print("No matching tool found for this QR code.")
    return None

def regenerate_qr_codes():
    tools = Tool.query.all()
    for tool in tools:
        qr_code = generate_qr_code(tool)
        tool.qr_code = qr_code
    db.session.commit()
    print("QR codes regenerated for all tools.")

def add_user(username, password, is_admin=False):
    if User.query.filter_by(username=username).first():
        print('Username already exists.')
        return
    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"User '{username}' added{' as admin' if is_admin else ''}.")

def is_admin(user_id):
    user = db.session.get(User, user_id)
    return user.is_admin if user else False

def add_admin(username, password):
    add_user(username, password, is_admin=True)

def remove_user(user_id):
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        print(f"User ID '{user_id}' removed.")
    else:
        print(f"User ID '{user_id}' not found.")

def list_users():
    users = User.query.all()
    for user in users:
        print(f"User ID: {user.id}, Username: {user.username}")

def logs():
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    open(LOG_FILE_PATH, 'a').close()
    logging.basicConfig(
        filename=LOG_FILE_PATH, 
        level=logging.INFO, 
        format='%(asctime)s %(levelname)s: %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def log_event(event_type, user_id, tool_id, additional_info=""):
    user = User.query.get(user_id)
    tool = Tool.query.get(tool_id)
    if user and tool:
        logging.info(f"{event_type}: User {user.username} ({user_id}) - Tool {tool.name} ({tool_id}) {additional_info}")
    else:
        logging.warning(f"{event_type}: Invalid user ID {user_id} or tool ID {tool_id}")

def log_lend_tool(user_id, tool_id):
    log_event("LEND", user_id, tool_id, f"on {datetime.datetime.now(datetime.timezone.utc)}")

def log_return_tool(user_id, tool_id):
    log_event("RETURN", user_id, tool_id, f"on {datetime.datetime.now(datetime.timezone.utc)}")

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out')
    return redirect(url_for('login'))

@app.route('/')
def index():
    borrowed_items = db.session.query(Transaction, Tool, User) \
                               .join(Tool, Transaction.tool_id == Tool.id) \
                               .join(User, Transaction.user_id == User.id) \
                               .filter(Transaction.return_date.is_(None)) \
                               .all()
    return render_template('index.html', borrowed_items=borrowed_items)

@app.context_processor
def utility_processor():
    def is_admin(user_id):
        user = db.session.get(User, user_id)
        return user.is_admin if user else False
    return dict(is_admin=is_admin)

@app.route('/inventory')
def inventory():
    tools = Tool.query.all()
    return render_template('inventory.html', tools=tools)

@app.route('/admin/live_logs')
def admin_live_logs():
    try:
        with open(LOG_FILE_PATH, 'r') as log_file:
            log_content = log_file.read()
        return log_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return str(e), 500

@app.route('/admin/download_logs', methods=['POST'])
def admin_download_logs():
    if os.path.exists(LOG_FILE_PATH):
        return send_file(LOG_FILE_PATH, as_attachment=True)
    else:
        flash('Log file not found', 'danger')
        return redirect(url_for('admin_panel'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Attempting login with username: {username}")
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User found: {user.username}")
            if user.check_password(password):
                session['user_id'] = user.id
                flash('Login successful', 'success')
                return redirect(url_for('lend'))
            else:
                flash('Incorrect password', 'danger')
        else:
            print("User not found")
            flash('Username not found', 'danger')
    return render_template('login.html')

@app.route('/lend', methods=['GET', 'POST'])
def lend():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'tool_id' in request.form:
            tool_id = request.form['tool_id']
        elif 'qr_data' in request.form:
            qr_data = request.form['qr_data']
            tool = Tool.query.filter_by(name=qr_data).first()
            if tool:
                tool_id = tool.id
            else:
                flash('Tool not found', 'danger')
                return redirect(url_for('lend'))
        else:
            flash('Invalid request', 'danger')
            return redirect(url_for('lend'))
        
        user_id = session['user_id']
        active_transaction = Transaction.query.filter_by(tool_id=tool_id, return_date=None).first()
        if active_transaction:
            flash('Tool is already lent out', 'danger')
        else:
            transaction = Transaction(user_id=user_id, tool_id=tool_id, borrow_date=datetime.datetime.now(datetime.timezone.utc))
            db.session.add(transaction)
            db.session.commit()
            log_lend_tool(user_id, tool_id)
            flash('Tool lent successfully', 'success')
    
    lent_out_tools = db.session.query(Transaction.tool_id).filter(Transaction.return_date.is_(None)).subquery()
    available_tools = Tool.query.filter(Tool.id.not_in(lent_out_tools.select())).all()

    borrowed_tools = db.session.query(Tool).join(Transaction).filter(Transaction.return_date.is_(None)).all()

    return render_template('lend.html', tools=available_tools, borrowed_tools=borrowed_tools)

@app.route('/return', methods=['GET', 'POST'])
def return_tool():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'tool_id' in request.form:
            tool_id = request.form['tool_id']
        elif 'qr_data' in request.form:
            qr_data = request.form['qr_data']
            tool = Tool.query.filter_by(name=qr_data).first()
            if tool:
                tool_id = tool.id
            else:
                flash('Tool not found', 'danger')
                return redirect(url_for('return_tool'))
        else:
            flash('Invalid request', 'danger')
            return redirect(url_for('return_tool'))
        
        transaction = Transaction.query.filter_by(tool_id=tool_id, return_date=None).first()
        if transaction:
            transaction.return_date = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()
            log_return_tool(transaction.user_id, tool_id) 
            flash('Tool returned successfully')
        else:
            flash('No active lending record found for this tool', 'danger')

    transactions = db.session.query(Transaction, Tool).join(Tool).filter(Transaction.return_date.is_(None)).all()
    borrowed_tools = [transaction.Tool for transaction in transactions]
    
    return render_template('return.html', transactions=transactions, borrowed_tools=borrowed_tools)

@app.route('/admin/download_qr_codes')
def download_qr_codes():
    # Create a BytesIO object to hold the zip file in memory
    zip_buffer = BytesIO()

    # Create a zip file within the BytesIO object
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        # Get all tools with QR codes
        tools = Tool.query.all()
        for tool in tools:
            qr_code_path = tool.qr_code
            if os.path.exists(qr_code_path):
                zip_file.write(qr_code_path, os.path.basename(qr_code_path))

    # Rewind the buffer's position to the beginning
    zip_buffer.seek(0)

    # Send the zip file to the client
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='qr_codes.zip')

@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect(url_for('login'))
    
    tools = Tool.query.all()
    users = User.query.all()
    return render_template('admin_panel.html', tools=tools, users=users)

@app.route('/admin/add_tool', methods=['POST'])
def admin_add_tool():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    name = request.form['tool_name']
    location = request.form['tool_location']
    add_tool(name, location)
    flash('Tool added successfully', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove_tool', methods=['POST'])
def admin_remove_tool():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    tool_id = request.form['tool_id']
    remove_tool(tool_id)
    flash('Tool removed successfully', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    username = request.form['username']
    password = request.form['password']
    add_user(username, password)
    flash('User added successfully', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove_user', methods=['POST'])
def admin_remove_user():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    user_id = request.form['user_id']
    remove_user(user_id)
    flash('User removed successfully', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/backup_database', methods=['POST'])
def admin_backup_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    backup_database()
    flash('Database backup created successfully', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/restore_database', methods=['POST'])
def admin_restore_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    backup_dir = os.path.join('backups')
    backups = sorted(os.listdir(backup_dir), reverse=True)
    if backups:
        latest_backup = os.path.join(backup_dir, backups[0])
        restore_database(latest_backup)
        flash('Database restored successfully', 'success')
    else:
        flash('No backup files found', 'danger')
    return redirect(url_for('admin_panel'))


def add_test_data():
    test_users = [
        {"username": "Alice", "password": "password1"},
        {"username": "Bob", "password": "password2"},
        {"username": "Charlie", "password": "password3"},
    ]

    test_tools = [
        {"name": "Hammer", "location": "Drawer 1"},
        {"name": "Screwdriver", "location": "Drawer 2"},
        {"name": "Wrench", "location": "Drawer 3"},
        {"name": "Drill", "location": "Under Desk 1"},
        {"name": "Saw", "location": "Drawer 4"},
        {"name": "Pliers", "location": "Drawer 5"},
        {"name": "Tape Measure", "location": "Drawer 6"},
        {"name": "Level", "location": "Drawer 7"},
        {"name": "Chisel", "location": "Drawer 8"},
        {"name": "Utility Knife", "location": "Under Desk 2"},
    ]

    for user in test_users:
        add_user(user["username"], user["password"])

    for tool in test_tools:
        add_tool(tool["name"], tool["location"])

    print("Test data added: 3 users and 10 tools.")

def run_console():
    try:
        with app.app_context():
            while True:
                print("\nTool Management System")
                print("1. Add Tool")
                print("2. Remove Tool")
                print("3. List Tools")
                print("4. Add User")
                print("5. Remove User")
                print("6. List Users")
                print("7. Identify Tool")
                print("10. Add Test Data")
                print("11. Regenerate QR Codes")
                print("12. Backup Database")
                print("13. Restore Database")
                print("14. Add Admin")
                print("15. Exit")
                choice = input("Enter your choice: ")

                if choice == '1':
                    name = input("Enter tool name: ")
                    location = input("Enter tool location: ")
                    add_tool(name, location)
                elif choice == '2':
                    tool_id = int(input("Enter tool ID to remove: "))
                    remove_tool(tool_id)
                elif choice == '3':
                    list_tools()
                elif choice == '4':
                    username = input("Enter user name: ")
                    password = input("Enter password: ")
                    add_user(username, password)
                elif choice == '5':
                    user_id = int(input("Enter user ID to remove: "))
                    remove_user(user_id)
                elif choice == '6':
                    list_users()
                elif choice == '7':
                    filename = input("Enter QR code filename: ")
                    file_path = os.path.join('static', 'qr_codes', filename)
                    print(f"Reading QR code from: {file_path}")
                    identify_tool_from_qr_code(file_path)
                elif choice == '10':
                    add_test_data()
                elif choice == '11':
                    regenerate_qr_codes()
                elif choice == '12':
                    backup_database()
                elif choice == '13':
                    backup_file = input("Enter the backup file path: ")
                    restore_database(backup_file)
                elif choice == '14':
                    username = input("Enter admin username: ")
                    password = input("Enter admin password: ")
                    add_user(username, password, is_admin=True)
                elif choice == '15':
                    shutdown_server()
                    break
                else:
                    print("Invalid choice. Please try again.")
    except KeyboardInterrupt:
        shutdown_server()



if __name__ == '__main__':
    def run_web_server():
        context = ('certs/certificate.pem', 'certs/key.pem')
        app.run(debug=True, ssl_context=context, host='0.0.0.0', port=5000,use_reloader=False)
    
    logs()

    web_thread = threading.Thread(target=run_web_server)
    web_thread.start()

    run_console()