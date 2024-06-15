from config import create_app
import utils
import views
import admin
import threading
import os
import logging

def run_console(app):
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
                print("16. reset items")
                choice = input("Enter your choice: ")

                if choice == '1':
                    name = input("Enter tool name: ")
                    location = input("Enter tool location: ")
                    utils.add_tool(name, location)
                elif choice == '2':
                    tool_id = int(input("Enter tool ID to remove: "))
                    utils.remove_tool(tool_id)
                elif choice == '3':
                    utils.list_tools()
                elif choice == '4':
                    username = input("Enter user name: ")
                    password = input("Enter password: ")
                    utils.add_user(username, password)
                elif choice == '5':
                    user_id = int(input("Enter user ID to remove: "))
                    utils.remove_user(user_id)
                elif choice == '6':
                    utils.list_users()
                elif choice == '7':
                    filename = input("Enter QR code filename: ")
                    file_path = os.path.join('static', 'qr_codes', filename)
                    print(f"Reading QR code from: {file_path}")
                    utils.identify_tool_from_qr_code(file_path)
                elif choice == '10':
                    utils.add_test_data()
                elif choice == '11':
                    utils.regenerate_qr_codes()
                elif choice == '12':
                    utils.backup_database(app)  # Pass the app instance here
                elif choice == '13':
                    backup_file = input("Enter the backup file path: ")
                    utils.restore_database(app, backup_file)  # Pass the app instance here
                elif choice == '14':
                    username = input("Enter admin username: ")
                    password = input("Enter admin password: ")
                    utils.add_user(username, password, is_admin=True)
                elif choice == '15':
                    utils.shutdown_server()
                    break
                elif choice == '16':
                    utils.reset_rented_items()
                else:
                    print("Invalid choice. Please try again.")
    except KeyboardInterrupt:
        utils.shutdown_server()

if __name__ == '__main__':
    app = create_app()

    def run_web_server():
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        context = ('certs/certificate.pem', 'certs/key.pem')
        app.run(debug=True, ssl_context=context, host='0.0.0.0', port=5000, use_reloader=False)

    web_thread = threading.Thread(target=run_web_server)
    web_thread.start()

    run_console(app)
