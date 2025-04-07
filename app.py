from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bingo-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bingo.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
socketio = SocketIO(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    dni = db.Column(db.String(9), nullable=False)

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    multiplayer = db.Column(db.Boolean, default=False)
    num_cards = db.Column(db.Integer, default=1)
    room_code = db.Column(db.String(10), nullable=True)

# --- LOGIN MANAGER ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- FUNCIONES DE BINGO ---
def generate_card():
    card = {}
    ranges = {'B': (1, 15), 'I': (16, 30), 'N': (31, 45), 'G': (46, 60), 'O': (61, 75)}
    for letter, (start, end) in ranges.items():
        card[letter] = random.sample(range(start, end+1), 5)
    card['N'][2] = 'FREE'
    return card

# --- RUTAS ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        dni = request.form['dni']
        mayor_edad = request.form.get('mayor_edad')
        if not mayor_edad:
            flash("Debes confirmar que eres mayor de edad")
            return redirect(url_for('registro'))
        if User.query.filter_by(username=username).first():
            flash("El usuario ya existe")
            return redirect(url_for('registro'))
        new_user = User(username=username, dni=dni)
        db.session.add(new_user)
        db.session.commit()
        flash("Registro exitoso")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        dni = request.form['dni']
        user = User.query.filter_by(username=username, dni=dni).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Credenciales incorrectas")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        num_cards = int(request.form['cantidad_cartones'])
        new_session = GameSession(user_id=current_user.id, num_cards=num_cards, multiplayer=False)
        db.session.add(new_session)
        db.session.commit()
        return redirect(url_for('game', game_id=new_session.id))
    return render_template('dashboard.html', usuario_id=current_user.id)

@app.route('/multijugador')
@login_required
def multijugador():
    room_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
    new_session = GameSession(user_id=current_user.id, num_cards=1, multiplayer=True, room_code=room_code)
    db.session.add(new_session)
    db.session.commit()
    return redirect(url_for('game', game_id=new_session.id))

@app.route('/game/<int:game_id>')
@login_required
def game(game_id):
    game_session = GameSession.query.get_or_404(game_id)
    cards = [generate_card() for _ in range(game_session.num_cards)]
    return render_template('game.html', game=game_session, cards=cards)

@app.route('/partidas/<int:usuario_id>')
@login_required
def partidas(usuario_id):
    sessions = GameSession.query.filter_by(user_id=usuario_id).all()
    return render_template('partidas.html', partidas=sessions)

# --- SOCKET.IO ---
@socketio.on('join_game')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('user_joined', {'msg': f"{current_user.username} se ha unido."}, to=room)

@socketio.on('start_game')
def handle_start(data):
    room = data['room']
    numbers = list(range(1, 76))
    random.shuffle(numbers)
    for num in numbers:
        emit('new_number', {'number': num}, to=room)
        socketio.sleep(3)

# --- MAIN ---
if __name__ == '__main__':
    # Asegurarse de que la aplicación está en el contexto adecuado
    with app.app_context():
        db.create_all()  # Crea las tablas de la base de datos si no existen
    socketio.run(app, debug=True)
