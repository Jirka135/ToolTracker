import qrcode
import random
import string
import os
import datetime
from io import BytesIO
import zipfile
import logging
from flask import send_file
from models import db, Tool, User, Transaction, ToolLog
import sqlite3
import cv2
from pyzbar.pyzbar import decode
from flask import request,current_app

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def log_event(event_type, user, tool, duration=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    formatted_timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    log_message = f"{formatted_timestamp} - {event_type}: User {user.username} ({user.id}) - Tool {tool.name} ({tool.id})"
    if duration:
        log_message += f" - Duration: {duration}"
    print(log_message)  # Print to console for immediate feedback

    log_entry = ToolLog(
        tool_name=tool.name,
        username=user.username,
        action=event_type,
        details=f"Time Lended: {duration}" if duration else None,
        timestamp=now
    )
    db.session.add(log_entry)
    db.session.commit()

def log_lend_tool(user_id, tool_id):
    user = User.query.get(user_id)
    tool = Tool.query.get(tool_id)
    if user and tool:
        tool.rented_by = user.username
        db.session.commit()
        log_event("LEND", user, tool)

def reset_rented_items():
    tools = Tool.query.filter(Tool.rented_by.isnot(None)).all()
    for tool in tools:
        tool.rented_by = None
    db.session.commit()
    print("All rented items have been reset to not rented.")

def log_return_tool(user_id, tool_id):
    user = User.query.get(user_id)
    tool = Tool.query.get(tool_id)
    
    if not user:
        print(f"User with ID {user_id} not found.")
        return
    
    if not tool:
        print(f"Tool with ID {tool_id} not found.")
        return
    
    transaction = Transaction.query.filter_by(user_id=user_id, tool_id=tool_id, return_date=None).first()
    if transaction:
        print(f"Transaction return_date before update: {transaction.return_date.strftime('%Y-%m-%d %H:%M:%S') if transaction.return_date else 'None'}")
        print(f"Found active transaction for user ID {user_id} and tool ID {tool_id}.")
        print(f"Current return_date: {transaction.return_date.strftime('%Y-%m-%d %H:%M:%S') if transaction.return_date else 'None'}")

        if transaction.borrow_date.tzinfo is None:
            transaction.borrow_date = transaction.borrow_date.replace(tzinfo=datetime.timezone.utc)

        duration_td = datetime.datetime.now(datetime.timezone.utc) - transaction.borrow_date
        hours, remainder = divmod(duration_td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{int(hours)}h:{int(minutes)}m:{int(seconds)}s"
        
        transaction.return_date = datetime.datetime.now(datetime.timezone.utc)
        tool.rented_by = None
        db.session.commit()
        log_event("RETURN", user, tool, duration_str)
        print(f"Tool {tool.name} returned by {user.username}.")
        print(f"Transaction return_date after update: {transaction.return_date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"No active transaction found for user ID {user_id} and tool ID {tool_id}.")



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
    
    qr_code_dir = current_app.config['QR_CODES_PATH']
    os.makedirs(qr_code_dir, exist_ok=True)
    
    qr_code_filename = f"{tool.name}_{tool.id}_{tool.location.replace(' ', '_')}_QRcode.png"
    qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
    
    img.save(qr_code_path)
    return qr_code_path

def add_tool(name, location, rented_by=None):
    new_tool = Tool(name=name, location=location, qr_code="placeholder", rented_by=rented_by)
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

def remove_tools(tool_ids):
    for tool_id in tool_ids:
        tool = Tool.query.get(tool_id)
        if tool:
            db.session.delete(tool)
    db.session.commit()

def remove_users(user_ids):
    for user_id in user_ids:
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
    db.session.commit()

def backup_database(app):
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f'database_backup_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.db')
    conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    with open(backup_file, 'wb') as f:
        for line in conn.iterdump():
            f.write(f'{line}\n'.encode('utf-8'))
    print(f"Backup created at {backup_file}")

def restore_database(app, backup_file):
    conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    cursor = conn.cursor()
    with open(backup_file, 'r') as f:
        sql = f.read()
        cursor.executescript(sql)
    conn.commit()
    print(f"Database restored from {backup_file}")

def generate_qr_codes_zip():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        tools = Tool.query.all()
        for tool in tools:
            qr_code_path = tool.qr_code
            if os.path.exists(qr_code_path):
                zip_file.write(qr_code_path, os.path.basename(qr_code_path))
    zip_buffer.seek(0)
    return zip_buffer

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

    rented_tools = [
        {"name": "Hammer", "location": "Drawer 1", "rented_by": "Alice"},
        {"name": "Screwdriver", "location": "Drawer 2", "rented_by": "Bob"},
    ]

    for tool in test_tools:
        add_tool(tool["name"], tool["location"])

    for tool in rented_tools:
        tool_instance = Tool.query.filter_by(name=tool["name"]).first()
        tool_instance.rented_by = tool["rented_by"]
        db.session.commit()

    print("Test data added: 3 users and 10 tools.")
