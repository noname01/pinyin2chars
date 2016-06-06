from flask import Flask, request, send_from_directory
import json
import random
import pinyin2chars
import smoothing

def load_from_json_file(fname):
    with open(fname) as f:
        content = f.readlines()
    data = u"".join(content)
    return json.loads(data)

print("Loading language model...")
candidate_map = load_from_json_file("candidate_map.json")
unigram_counts = load_from_json_file("unigram_counts.json")
bigram_counts = load_from_json_file("bigram_counts.json")
print("Initalizing smoothed counts...")
lp_smoother = smoothing.Laplace(unigram_counts, bigram_counts)
wb_smoother = smoothing.WittenBell(unigram_counts, bigram_counts)
gt_smoother = smoothing.GoodTuring(unigram_counts, bigram_counts, load_from_json_file("gt_smoothed_counts.json"))
test_bitext = load_from_json_file("test_bitext.json")
smoothers = {"laplace": lp_smoother, "wittenbell": wb_smoother, "goodturing": gt_smoother}

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
    smoother = smoothers[request.args.get('smoothing')]
    chars = pinyin2chars.convert_bigram_dp(pinyin_str, smoother, candidate_map)
    if chars == None:
        return "Invalid input or no decoding found."
    return u"|".join(chars)
    return test_str

@app.route('/bitext')
def bitext_api():
    sample_size = int(request.args.get('size'))
    rand_smpl = [ test_bitext[i] for i in random.sample(xrange(len(test_bitext)), sample_size) ]
    return json.dumps(rand_smpl)

if __name__ == "__main__":
    app.run()