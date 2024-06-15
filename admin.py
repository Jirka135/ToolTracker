from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, session
from models import db, Tool, User, ToolLog
import os
from utils import (add_tool, remove_tool, add_user, remove_user, is_admin, backup_database, 
                   restore_database, download_qr_codes, log_lend_tool, log_return_tool)

admin_bp = Blueprint('admin', __name__)

@admin_bp.context_processor
def utility_processor():
    def is_admin(user_id):
        user = db.session.get(User, user_id)
        return user.is_admin if user else False
    return dict(is_admin=is_admin)

@admin_bp.route('/admin_panel')
def admin_panel():
    tools = Tool.query.all()
    users = User.query.all()
    logs = ToolLog.query.order_by(ToolLog.timestamp.desc()).all()

    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user': log.user.username,
            'tool': log.tool.name,
            'action': log.action,
            'details': log.details if log.details else "None"
        })

    return render_template('admin_panel.html', tools=tools, users=users, logs=formatted_logs)

@admin_bp.route('/add_tool', methods=['POST'])
def admin_add_tool():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    name = request.form['tool_name']
    location = request.form['tool_location']
    add_tool(name, location)
    flash('Tool added successfully', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/remove_tool', methods=['POST'])
def admin_remove_tool():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    tool_id = request.form['tool_id']
    remove_tool(tool_id)
    flash('Tool removed successfully', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/add_user', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    username = request.form['username']
    password = request.form['password']
    add_user(username, password)
    flash('User added successfully', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/remove_user', methods=['POST'])
def admin_remove_user():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    user_id = request.form['user_id']
    remove_user(user_id)
    flash('User removed successfully', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/backup_database', methods=['POST'])
def admin_backup_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    backup_database()
    flash('Database backup created successfully', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/restore_database', methods=['POST'])
def admin_restore_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    backup_dir = os.path.join('backups')
    backups = sorted(os.listdir(backup_dir), reverse=True)
    if backups:
        latest_backup = os.path.join(backup_dir, backups[0])
        restore_database(latest_backup)
        flash('Database restored successfully', 'success')
    else:
        flash('No backup files found', 'danger')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/download_qr_codes')
def admin_download_qr_codes():
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect(url_for('views.login'))
    
    return download_qr_codes()

@admin_bp.route('/live_logs')
def admin_live_logs():
    try:
        with open('instance/app.log', 'r') as log_file:
            log_content = log_file.read()
        return log_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return str(e), 500

from flask import send_file
import io

@admin_bp.route('/download_logs')
def download_logs():
    logs = ToolLog.query.order_by(ToolLog.timestamp.desc()).all()

    log_lines = []
    for log in logs:
        timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        user = log.user.username
        tool = log.tool.name
        action = log.action
        details = log.details if log.details else "None"
        log_lines.append(f"{timestamp} - {user} - {tool} - Action: {action} - Details: {details}")

    log_content = "\n".join(log_lines)

    buffer = io.BytesIO()
    buffer.write(log_content.encode('utf-8'))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='logs.txt', mimetype='text/plain')
