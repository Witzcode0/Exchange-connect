from app import create_app, sockio
from gevent import monkey
monkey.patch_all()  # required for socketio

socketapp = create_app('socket_config', socket=True)

if __name__ == '__main__':
    sockio.run(socketapp, debug=socketapp.debug, port=socketapp.config['PORT'])
