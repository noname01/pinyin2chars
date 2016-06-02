from flask import Flask, request, send_from_directory

import pinyin2chars

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('web', path)

@app.route('/')
def root():
    return send_from_directory('web', 'index.html')

@app.route('/decode')
def decode_api():
	pinyins = request.args.get('pinyins')
	print pinyins
	return pinyin2chars.decode_pinyin(pinyins)

if __name__ == "__main__":
    app.run()