import collections
import copy

import sqlqueries

def cid_to_sid(cid):
    return cid[:cid.index("-")]

def format_cid(ids):
    word_num = str(ids[2]).zfill(3)
    char_num = str(ids[3]).zfill(2)
    return "{}.{}-{}:{}".format(str(ids[0]), str(ids[1]), word_num, char_num)

def format_pair(chars):
    return chars[0] + u"#" + unicode(chars[1])

# Bitext: list(list(str)), a list of text segments / utterances.
# Each str has the form: "char#pinyin", or "x#x" where is_cjk of x = "N"
def get_bitext_corpus():
    print "Loading bitext..."
    # Query returns a list of tuples (cid, "char#pinyin"). Punctuations excluded.
    # cid = "file_id.sentence_id.word_num.char_num"
    cid_map = {}
    training_chars = set()
    for tup in sqlqueries.get_bitext():
    	cid_map[format_cid(tup[0:4])] = format_pair(tup[4:6])
        training_chars.add(tup[4])
    # Query returns non-cjk chars. The value is "x#x".
    nonchar_cids = set()
    
    for tup in sqlqueries.get_nonchars():
        cid = format_cid(tup[0:4])
    	cid_map[cid] = format_pair(tup[4:6])
    	# Special symbols like numbers where token_type = w should be added.
        if (tup[6] != "w"):
            nonchar_cids.add(cid)
        else:
            training_chars.add(tup[4]);
    res = []
    cur_segment = []
    last_sid = None
    for cid in sorted(cid_map.keys()):
        if cur_segment and ((cid in nonchar_cids) or (last_sid and last_sid != cid_to_sid(cid))):
            res.append(copy.deepcopy(cur_segment))
            cur_segment = []
            last_sid = None
        if not cid in nonchar_cids:
            cur_segment.append(cid_map[cid])
            last_sid = cid_to_sid(cid)           
    if (cur_segment):
        res.append(copy.deepcopy(cur_segment))
    # print u" ".join(training_chars)
    print "Done."
    print "{} text segments parsed.".format(str(len(res)))
    print "{} unique characters found.".format(str(len(training_chars)))
    return res

# Builds a map from pinyins to candidate characters.
# Have the whole mapp in memory therefore subsequent lookups are fast.
# res: dict(str->list(str))
def init_candidate_map():
    print "building candidate map..."
    res = {}
    for tup in sqlqueries.get_candidate_chars():
        if (not tup[0] in res):
            res[tup[0]] = []
        res[tup[0]].append(tup[1])
    print "Done."
    return res

# text: list(list(tokens))
# Generates a dictionary that maps n-grams to counts.
# Keys: n-grams separated by spaces.
def get_ngram_counts(text, n):
    print "Generating {}-gram model...".format(str(n))
    ngram_counts = {}
    for segment in text:
        # add start and end symbols
        line = copy.deepcopy(segment)
        line.insert(0, "<s>")
        line.insert(len(line), "</s>")
        head = 0
        while (head + n <= len(line)):
            gram = u" ".join(line[head:head+n])
            ngram_counts[gram] = ngram_counts.get(gram, 0) + 1
            head += 1
    print "Done."
    return ngram_counts

# Laplace for now
# Returns a real number.
def get_smoothed_count(raw_count_map, gram):
    return raw_count_map.get(gram, 0) + 1.0

def get_cond_prob_bigram(w1, w2, unigram_counts, bigram_counts):
    return get_smoothed_count(w1 + u" " + w2) / get_smoothed_count(w1)

bitext = get_bitext_corpus()
candidate_map = init_candidate_map()

unigram_counts = get_ngram_counts(bitext, 1)
bigram_counts = get_ngram_counts(bitext, 2)

for key in candidate_map.keys():
    print key + ": " + u" ".join(candidate_map[key])