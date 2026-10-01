import json
import csv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    Response
)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

# -----------------------------
# CONFIGURATION
# -----------------------------
app.config['SECRET_KEY'] = 'expense_tracker_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------
# LOGIN MANAGER
# -----------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# -----------------------------
# USER MODEL
# -----------------------------
class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    email = db.Column(
    db.String(120),
    unique=True,
    nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

# -----------------------------
# TRANSACTION MODEL
# -----------------------------
class Transaction(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(100),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    type = db.Column(
        db.String(20),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

# -----------------------------
# USER LOADER
# -----------------------------
@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )
# -----------------------------
# REGISTER PAGE
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        email = request.form['email']

        password = generate_password_hash(
            request.form['password']
        )

        user = User(
            email=email,
            password=password
        )

        db.session.add(user)

        db.session.commit()

        return redirect('/login')

    return render_template(
        'register.html'
    )
# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        print("Email:", email)

        user = User.query.filter_by(
            email=email
            ).first()

        print("User Found:", user)

        if user:

            password_ok = check_password_hash(
                user.password,
                password
            )

            print("Password Match:", password_ok)

            if password_ok:

                login_user(user)

                print("LOGIN SUCCESS")

                return redirect('/')

        print("LOGIN FAILED")

    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']
        new_password = request.form['password']

        user = User.query.filter_by(
            email=email
            ).first()

        if user:

            user.password = generate_password_hash(
                new_password
            )

            db.session.commit()

            return redirect('/login')

    return render_template(
        'forgot_password.html'
    )
# -----------------------------
# HOME PAGE
# -----------------------------
@app.route('/')
@login_required
def home():

    search = request.args.get(
        'search',
        ''
    )

    if search:

        transactions = Transaction.query.filter_by(
            user_id=current_user.id
            ).filter(
                Transaction.title.contains(search)
                ).order_by(
                    Transaction.id.desc()
                    ).all()

    else:

        transactions = Transaction.query.filter_by(
        user_id=current_user.id
        ).order_by(
            Transaction.id.desc()
            ).all()

    total_income = sum(
        t.amount
        for t in transactions
        if t.type == 'Income'
    )

    total_expense = sum(
        t.amount
        for t in transactions
        if t.type == 'Expense'
    )

    balance = total_income - total_expense

    category_totals = {}

    for transaction in transactions:

        if transaction.type == "Expense":

            if transaction.category in category_totals:

                category_totals[
                    transaction.category
                ] += transaction.amount

            else:

                category_totals[
                    transaction.category
                ] = transaction.amount

    return render_template(
        'index.html',
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        chart_labels=json.dumps(
            list(category_totals.keys())
        ),
        chart_values=json.dumps(
            list(category_totals.values())
        ),
        search=search
    )

# -----------------------------
# ADD TRANSACTION
# -----------------------------
@app.route('/add', methods=['POST'])
@login_required
def add_transaction():

    title = request.form['title']

    amount = float(
        request.form['amount']
    )

    category = request.form['category']

    transaction_type = request.form['type']

    date = datetime.strptime(
        request.form['date'],
        '%Y-%m-%d'
    ).date()

    transaction = Transaction(
    title=title,
    amount=amount,
    category=category,
    type=transaction_type,
    date=date,
    user_id=current_user.id
    )

    db.session.add(transaction)

    db.session.commit()

    return redirect('/')

# -----------------------------
# EDIT TRANSACTION
# -----------------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    if request.method == 'POST':

        transaction.title = request.form['title']

        transaction.amount = float(
            request.form['amount']
        )

        transaction.category = request.form['category']

        transaction.type = request.form['type']

        db.session.commit()

        return redirect('/')

    return render_template(
        'edit.html',
        transaction=transaction
    )

# -----------------------------
# DELETE TRANSACTION
# -----------------------------
@app.route('/delete/<int:id>')
@login_required
def delete_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    db.session.delete(transaction)

    db.session.commit()

    return redirect('/')

# -----------------------------
# EXPORT CSV
# -----------------------------
@app.route('/export')
@login_required
def export_csv():

    transactions = Transaction.query.all()

    def generate():

        yield 'ID,Title,Amount,Category,Date,Type\n'

        for t in transactions:

            yield (
                f'{t.id},'
                f'{t.title},'
                f'{t.amount},'
                f'{t.category},'
                f'{t.date},'
                f'{t.type}\n'
            )

    return Response(
        generate(),
        mimetype='text/csv',
        headers={
            'Content-Disposition':
            'attachment; filename=transactions.csv'
        }
    )

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect('/login')

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':

    with app.app_context():

        db.create_all()

    app.run(
        debug=True
    )