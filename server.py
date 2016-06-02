from flask import Flask, request, send_from_directory
import json
import pinyin2chars

def load_from_json_file(fname):
    with open(fname) as f:
        content = f.readlines()
    data = u"".join(content)
    return json.loads(data)

candidate_map = load_from_json_file("candidate_map.json")
unigram_counts = load_from_json_file("unigram_counts.json")
bigram_counts = load_from_json_file("bigram_counts.json")

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
    pinyin_str = request.args.get('pinyins')
    chars = pinyin2chars.convert_bigram_dp(pinyin_str, unigram_counts, bigram_counts, candidate_map)
    if chars == None:
        return "Invalid input or no decoding found."
    return u"|".join(chars)
    return test_str

if __name__ == "__main__":
    app.run()