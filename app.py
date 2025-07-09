from flask import Flask, render_template, request, redirect, url_for, session
import os, uuid, subprocess
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'user_sessions'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------
# Home: Upload Page
# ---------------------
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if not file.filename.endswith('.py'):
            return "Only .py files allowed!", 400
        
        # Unique folder for user
        user_id = str(uuid.uuid4())
        user_folder = os.path.join(UPLOAD_FOLDER, user_id)
        os.makedirs(user_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(user_folder, 'bot.py')
        file.save(file_path)
        
        # Store user folder in session
        session['user_folder'] = user_folder
        
        return redirect(url_for('token_input'))
    
    return render_template('upload.html')

# ---------------------
# Token Input Page
# ---------------------
@app.route('/token', methods=['GET', 'POST'])
def token_input():
    if 'user_folder' not in session:
        return redirect(url_for('upload_file'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        action = request.form.get('action')
        
        if action == 'skip':
            session['token'] = None
        else:
            token_file = os.path.join(session['user_folder'], 'token.txt')
            with open(token_file, 'w') as f:
                f.write(token)
            session['token'] = token
        
        return redirect(url_for('console'))
    
    return render_template('token.html')

# ---------------------
# Console Page
# ---------------------
@app.route('/console')
def console():
    if 'user_folder' not in session:
        return redirect(url_for('upload_file'))
    return render_template('console.html')

# ---------------------
# Start Bot
# ---------------------
@socketio.on('start_bot')
def handle_start_bot():
    user_folder = session.get('user_folder')
    if not user_folder:
        emit('console_output', 'Error: No session found!')
        return
    
    token = session.get('token')
    if not token:
        emit('console_output', 'Error: Bot token required! (Skipped)')
        return
    
    # Run bot script using subprocess
    process = subprocess.Popen(
        ['python3', 'bot.py'],
        cwd=user_folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    for line in process.stdout:
        emit('console_output', line)
    
    process.wait()
    emit('console_output', 'Bot process finished.')

if __name__ == '__main__':
    socketio.run(app, debug=True)
