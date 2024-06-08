from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import cv2
from pyzbar.pyzbar import decode
import random
import string


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    qr_code = db.Column(db.String(120), unique=True, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    qr_code = db.Column(db.String(120), unique=True, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)

# Create the database tables within the app context
with app.app_context():
    db.create_all()

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Ensure the directory exists
    qr_code_dir = os.path.join('static', 'qr_codes')
    os.makedirs(qr_code_dir, exist_ok=True)
    
    # Generate a unique filename
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    qr_code_filename = f'{data}_QRcode_{random_suffix}.png'
    qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
    
    img.save(qr_code_path)
    return qr_code_path

def add_tool(name):
    qr_code = generate_qr_code(name)
    new_tool = Tool(name=name, qr_code=qr_code)
    db.session.add(new_tool)
    db.session.commit()
    print(f"Tool '{name}' added with QR code.")

def remove_tool(tool_id):
    tool = Tool.query.get(tool_id)
    if tool:
        db.session.delete(tool)
        db.session.commit()
        print(f"Tool ID '{tool_id}' removed.")
    else:
        print(f"Tool ID '{tool_id}' not found.")

def list_tools():
    tools = Tool.query.all()
    for tool in tools:
        print(f"Tool ID: {tool.id}, Name: {tool.name}, QR Code: {tool.qr_code}")

def add_user(name):
    qr_code = generate_qr_code(name)
    new_user = User(name=name, qr_code=qr_code)
    db.session.add(new_user)
    db.session.commit()
    print(f"User '{name}' added with QR code.")

def remove_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        print(f"User ID '{user_id}' removed.")
    else:
        print(f"User ID '{user_id}' not found.")

def list_users():
    users = User.query.all()
    for user in users:
        print(f"User ID: {user.id}, Name: {user.name}, QR Code: {user.qr_code}")

def generate_qr_code_for_tool(tool_id):
    tool = Tool.query.get(tool_id)
    if tool:
        qr_code_path = generate_qr_code(tool.name)
        tool.qr_code = qr_code_path
        db.session.commit()
        print(f"QR code for Tool ID '{tool_id}' generated and saved at '{qr_code_path}'.")
    else:
        print(f"Tool ID '{tool_id}' not found.")

def identify_tool_from_qr_code(file_path):
    img = cv2.imread(file_path)
    decoded_objects = decode(img)
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        tool = Tool.query.filter_by(name=qr_data).first()
        if tool:
            print(f"QR code corresponds to Tool ID: {tool.id}, Name: {tool.name}")
            return tool
    print("No matching tool found for this QR code.")
    return None

def test_add_data():
    tools = [
        "Hammer", "Screwdriver", "Wrench", "Drill", "Saw", 
        "Pliers", "Tape Measure", "Level", "Chisel", "Utility Knife"
    ]
    users = ["Alice", "Bob", "Charlie"]

    # Add tools
    for tool_name in tools:
        add_tool(tool_name)
    
    # Add users
    for user_name in users:
        add_user(user_name)

    print("Test data added: 10 tools and 3 users.")

if __name__ == '__main__':
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
            print("8. Generate QR Code")
            print("exit Exit")
            choice = input("Enter your choice: ")

            if choice == '1':
                name = input("Enter tool name: ")
                add_tool(name)
            elif choice == '2':
                tool_id = int(input("Enter tool ID to remove: "))
                remove_tool(tool_id)
            elif choice == '3':
                list_tools()
            elif choice == '4':
                name = input("Enter user name: ")
                add_user(name)
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
            elif choice == '8':
                list_tools()
                tool_id = int(input("Enter tool ID to remove: "))
                generate_qr_code_for_tool(tool_id)
            elif choice == 'exit':
                break
            else:
                print("Invalid choice. Please try again.")
