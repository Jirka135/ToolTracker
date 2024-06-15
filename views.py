from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Tool, User, Transaction
from utils import log_lend_tool, log_return_tool
import datetime

views_bp = Blueprint('views', __name__)

@views_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('views.login'))

@views_bp.route('/')
def index():
    borrowed_items = db.session.query(Transaction, Tool, User) \
                               .join(Tool, Transaction.tool_id == Tool.id) \
                               .join(User, Transaction.user_id == User.id) \
                               .filter(Transaction.return_date.is_(None)) \
                               .all()
    return render_template('index.html', borrowed_items=borrowed_items)

@views_bp.context_processor
def utility_processor():
    def is_admin(user_id):
        user = db.session.get(User, user_id)
        return user.is_admin if user else False
    return dict(is_admin=is_admin)

@views_bp.route('/inventory')
def inventory():
    tools = Tool.query.all()
    return render_template('inventory.html', tools=tools)

@views_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('Incorrect username', 'danger')
        elif not user.check_password(password):
            flash('Incorrect password', 'danger')
        else:
            session['user_id'] = user.id
            flash('Login successful', 'success')
            return redirect(url_for('views.lend'))
    return render_template('login.html')

@views_bp.route('/lend', methods=['GET', 'POST'])
def lend():
    if 'user_id' not in session:
        return redirect(url_for('views.login'))
    
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
                return redirect(url_for('views.lend'))
        else:
            flash('Invalid request', 'danger')
            return redirect(url_for('views.lend'))
        
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

@views_bp.route('/return', methods=['GET', 'POST'])
def return_tool():
    if 'user_id' not in session:
        return redirect(url_for('views.login'))

    if request.method == 'POST':
        tool_id = request.form.get('tool_id')
        qr_data = request.form.get('qr_data')

        if tool_id:
            tool = Tool.query.get(tool_id)
        elif qr_data:
            tool = Tool.query.filter_by(name=qr_data).first()
        else:
            tool = None

        if tool:
            transaction = Transaction.query.filter_by(tool_id=tool.id, return_date=None).first()
            if transaction:
                log_return_tool(transaction.user_id, tool.id)
                flash('Tool returned successfully', 'success')
            else:
                flash('No active lending record found for this tool', 'danger')
        else:
            flash('Tool not found', 'danger')

    # Fetch all transactions that are still active (not returned)
    transactions = db.session.query(Transaction, Tool).join(Tool).filter(Transaction.return_date.is_(None)).all()
    borrowed_tools = [tool for transaction, tool in transactions]

    return render_template('return.html', transactions=transactions, borrowed_tools=borrowed_tools)