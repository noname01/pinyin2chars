import collections
import copy

import sqlite3

import sqlqueries

connection = sqlite3.connect('data/lcmc.db3')
cursor = connection.cursor()


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
    for tup in cursor.execute(sqlqueries.GET_BITEXT):
    	cid_map[format_cid(tup[0:4])] = format_pair(tup[4:6])
        training_chars.add(tup[4])
    # Query returns non-cjk chars. The value is "x#x".
    nonchar_cids = set()
    
    for tup in cursor.execute(sqlqueries.GET_NONCHARS):
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

# text: list(list(tokens))
# Generates a dictionary that maps n-grams to counts.
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
            if not gram in ngram_counts:
                ngram_counts[gram] = 0
            ngram_counts[gram] += 1
            head += 1
    print "Done."
    return ngram_counts

def smooth_counts(counts):
    return counts

bitext = get_bitext_corpus()

unigram_counts = smooth_counts(get_ngram_counts(bitext, 1))
bigram_counts = smooth_counts(get_ngram_counts(bitext, 2))
