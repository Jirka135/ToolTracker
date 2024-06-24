from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, session,current_app
from models import db, Tool, User, ToolLog
import os
from utils import (add_tool, remove_tools, add_user, remove_users, is_admin, backup_database, 
                   restore_database, generate_qr_codes_zip, log_lend_tool, log_return_tool, regenerate_qr_codes)
import io

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
            'user': log.username,
            'tool': log.tool_name,
            'action': log.action,
            'details': log.details if log.details else "None"
        })

    return render_template('admin_panel.html', tools=tools, users=users, logs=formatted_logs)

@admin_bp.route('/manage_tools')
def manage_tools():
    tools = Tool.query.all()
    return render_template('manage_tools.html', tools=tools)

@admin_bp.route('/manage_users')
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/database_management')
def database_management():
    return render_template('database_management.html')

@admin_bp.route('/logs')
def logs():
    logs = ToolLog.query.order_by(ToolLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

@admin_bp.route('/qr_codes')
def qr_codes():
    return render_template('qr_codes.html')

@admin_bp.route('/add_tool', methods=['POST'])
def admin_add_tool():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    name = request.form['tool_name']
    location = request.form['tool_location']
    add_tool(name, location)
    flash('Tool added successfully', 'success')
    return redirect(url_for('admin.manage_tools'))

@admin_bp.route('/remove_tools', methods=['POST'])
def admin_remove_tools():
    tool_ids = request.form.get('tool_ids')
    if tool_ids:
        ids = [int(id.strip()) for id in tool_ids.split(',')]
        remove_tools(ids)
        flash(f'Removed {len(ids)} tool(s)', 'success')
    else:
        flash('No tool IDs provided', 'danger')
    return redirect(url_for('admin.manage_tools'))

@admin_bp.route('/add_user', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    username = request.form['username']
    password = request.form['password']
    add_user(username, password)
    flash('User added successfully', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/remove_users', methods=['POST'])
def admin_remove_users():
    user_ids = request.form.get('user_ids')
    if user_ids:
        ids = [int(id.strip()) for id in user_ids.split(',')]
        remove_users(ids)
        flash(f'Removed {len(ids)} user(s)', 'success')
    else:
        flash('No user IDs provided', 'danger')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/backup_database', methods=['POST'])
def admin_backup_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    backup_database()
    flash('Database backup created successfully', 'success')
    return redirect(url_for('admin.database_management'))

@admin_bp.route('/restore_database', methods=['POST'])
def admin_restore_database():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    backup_dir = current_app.config['BACKUPS_PATH']
    backups = sorted(os.listdir(backup_dir), reverse=True)
    if backups:
        latest_backup = os.path.join(backup_dir, backups[0])
        restore_database(latest_backup)
        flash('Database restored successfully', 'success')
    else:
        flash('No backup files found', 'danger')
    return redirect(url_for('admin.database_management'))

@admin_bp.route('/download_qr_codes', methods=['GET','POST'])
def admin_download_qr_codes():
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect(url_for('views.login'))
    
    zip_buffer = generate_qr_codes_zip()
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='qr_codes.zip')

@admin_bp.route('/regenerate_qr_codes', methods=['POST'])
def admin_regenerate_qr_codes():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))
    
    regenerate_qr_codes()
    flash('QR codes regenerated successfully', 'success')
    return redirect(url_for('admin.qr_codes'))

@admin_bp.route('/live_logs')
def admin_live_logs():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Admin access required', 'danger')
        return redirect(url_for('views.login'))

    logs = ToolLog.query.order_by(ToolLog.timestamp.desc()).all()
    return render_template('live_logs.html', logs=logs)

@admin_bp.route('/download_logs')
def download_logs():
    logs = ToolLog.query.order_by(ToolLog.timestamp.desc()).all()

    log_lines = []
    for log in logs:
        timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        user = log.username
        tool = log.tool_name
        action = log.action
        details = log.details if log.details else "None"
        log_lines.append(f"{timestamp} - {user} - {tool} - Action: {action} - Details: {details}")

    log_content = "\n".join(log_lines)

    buffer = io.BytesIO()
    buffer.write(log_content.encode('utf-8'))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='logs.txt', mimetype='text/plain')
