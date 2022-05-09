from app import create_app

flaskapp = create_app('config')

if __name__ == '__main__':
    flaskapp.run(port=9990, host='0.0.0.0', debug=flaskapp.debug)
