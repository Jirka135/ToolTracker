from flask import Flask
from models import db
import views
import admin
import os
import subprocess
import urllib.request
import zipfile
import ssl
import sys
import socket

def download_openssl(openssl_dir):
    openssl_url = 'https://download.firedaemon.com/FireDaemon-OpenSSL/openssl-3.3.1.zip'
    openssl_zip_path = os.path.join(openssl_dir, 'openssl.zip')
    openssl_extract_path = os.path.join(openssl_dir, 'openssl')

    if not os.path.exists(openssl_extract_path):
        print("Downloading OpenSSL...")

        # Set up SSL context and user-agent header
        context = ssl._create_unverified_context()
        headers = {'User-Agent': 'Mozilla/5.0'}

        req = urllib.request.Request(openssl_url, headers=headers)

        with urllib.request.urlopen(req, context=context) as response, open(openssl_zip_path, 'wb') as out_file:
            out_file.write(response.read())

        print("Extracting OpenSSL...")
        with zipfile.ZipFile(openssl_zip_path, 'r') as zip_ref:
            zip_ref.extractall(openssl_extract_path)

        os.remove(openssl_zip_path)
        print("OpenSSL downloaded and extracted successfully.")


def get_self_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception as e:
        ip_address = '127.0.0.1'
        print(f"Error occurred: {e}")
    print(f"Host IP Address: {ip_address}")
    return ip_address

def create_app():
    BASE_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'ToolTracker')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'app.db')
    QR_CODES_PATH = os.path.join(BASE_DIR, 'qr_codes')
    BACKUPS_PATH = os.path.join(BASE_DIR, 'backups')
    CERTS_PATH = os.path.join(BASE_DIR, 'certs')
    OPENSSL_DIR = os.path.join(BASE_DIR, 'openssl')

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    os.makedirs(QR_CODES_PATH, exist_ok=True)
    os.makedirs(CERTS_PATH, exist_ok=True)
    os.makedirs(OPENSSL_DIR, exist_ok=True)

    # Check if OpenSSL is present and download if not
    openssl_executable = os.path.join(OPENSSL_DIR, 'openssl', 'openssl-3', 'x64', 'bin', 'openssl.exe')
    if not os.path.exists(openssl_executable):
        download_openssl(OPENSSL_DIR)

    certificate_path = os.path.join(CERTS_PATH, 'certificate.pem')
    key_path = os.path.join(CERTS_PATH, 'key.pem')

    if not os.path.exists(certificate_path) or not os.path.exists(key_path):
        print(f"Certificate or key file not found. Please create 'certificate.pem' and 'key.pem' in the folder: {CERTS_PATH}")
        choice = input("Do you want assistance with creating these files? (yes/no): ").strip().lower()
        if choice == 'yes':
            create_certificate_and_key(certificate_path, key_path, openssl_executable)
        else:
            input("Press Enter after you have placed the files in the folder...")

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['QR_CODES_PATH'] = QR_CODES_PATH
    app.config['BACKUPS_PATH'] = BACKUPS_PATH
    app.config['CERTS_PATH'] = CERTS_PATH
    app.config['OPENSSL_DIR'] = OPENSSL_DIR

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(views.views_bp)
    app.register_blueprint(admin.admin_bp)

    return app

def create_certificate_and_key(certificate_path, key_path, openssl_executable):
    try:
        # Path to the bundled OpenSSL config
        openssl_cnf_path = os.path.join(os.path.dirname(openssl_executable), '..', '..', '..', 'openssl-3', 'ssl', 'openssl.cnf')
        
        print(f"OpenSSL executable path: {openssl_executable}")
        print(f"OpenSSL config path: {openssl_cnf_path}")

        # Generate a new private key
        subprocess.run([openssl_executable, 'genpkey', '-algorithm', 'RSA', '-out', key_path, '-pkeyopt', 'rsa_keygen_bits:2048'], check=True)
        # Generate a new certificate signing request (CSR)
        subprocess.run([openssl_executable, 'req', '-new', '-key', key_path, '-out', 'csr.pem', '-subj', '/CN=localhost', '-config', openssl_cnf_path], check=True)
        # Generate a self-signed certificate
        subprocess.run([openssl_executable, 'x509', '-req', '-days', '365', '-in', 'csr.pem', '-signkey', key_path, '-out', certificate_path], check=True)
        # Remove the CSR file as it's no longer needed
        os.remove('csr.pem')
        print(f"Certificate and key have been created successfully in the folder: {os.path.dirname(certificate_path)}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while generating the certificate and key: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    except FileNotFoundError as fnf_error:
        print(f"OpenSSL not found: {fnf_error}")
        input("Press Enter to exit...")
        sys.exit(1)

