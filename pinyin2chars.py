#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import copy
import re
import json

from random import randint
from math import log

if __name__ == "__main__":
    import sqlqueries

import smoothing

def cid_to_sid(cid):
    return cid[:cid.index("-")]

def format_cid(ids):
    word_num = str(ids[2]).zfill(3)
    char_num = str(ids[3]).zfill(2)
    return u"{}.{}-{}:{}".format(unicode(ids[0]), unicode(ids[1]), word_num, char_num)

def format_pair(character, pinyin):
    if (character == "<s>" or character == "</s>"):
        return character
    return character + u"#" + pinyin

def bitext_segment_to_pinyin_str(segment):
    return u" ".join(map(lambda token : token.split(u"#")[1], segment))

def bitext_segment_to_char_str(segment):
    return u" ".join(map(lambda token : token.split(u"#")[0], segment))

# Bitext: list(list(str)), a list of text segments / utterances.
# Each str has the form: "char#pinyin", or "x#x" where is_cjk of x = "N"
# division: "trainig|dev|test"
def get_bitext_corpus(division):
    print("Loading " + division + " bitext...")
    # Query returns a list of tuples (cid, "char#pinyin"). Punctuations excluded.
    # cid = "file_id.sentence_id.word_num.char_num"
    cid_map = {}
    training_chars = set()
    for tup in sqlqueries.get_bitext(division):
        cid_map[format_cid(tup[0:4])] = format_pair(tup[4], tup[5])
        training_chars.add(tup[4])
    # Query returns non-cjk chars. The value is "x#x".
    nonchar_cids = set()
    
    for tup in sqlqueries.get_nonchars(division):
        cid = format_cid(tup[0:4])
        cid_map[cid] = format_pair(tup[4], tup[5])
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
    print("Done.")
    print("{} text segments parsed.".format(str(len(res))))
    print("{} unique characters found.".format(str(len(training_chars))))
    return res

# Builds a map from pinyins to candidate characters.
# Have the whole mapp in memory therefore subsequent lookups are fast.
# res: dict(str->list(str))
def init_candidate_map():
    print("building candidate map...")
    res = {}
    for tup in sqlqueries.get_candidate_chars():
        pinyin = tup[0]
        if tup[2] == "N":
            pinyin = tup[1]
        if (not pinyin in res):
            res[pinyin] = []
        if (not tup[1] in res[pinyin]):
            res[pinyin].append(tup[1])
    res["<s>"] = ["<s>"]
    res["</s>"] = ["</s>"]
    print("Done.")
    return res

# text: list(list(tokens))
# Generates a dictionary that maps n-grams to counts.
# Keys: n-grams separated by spaces.
def get_ngram_counts(text, n):
    print("Generating {}-gram model...".format(str(n)))
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
    print("Done.")
    return ngram_counts

# Baseline: randomly pick a candicate character
# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_baseline(pinyin_str, candidate_map):
    pinyins = re.split("\s+", pinyin_str)
    res = []
    for pinyin in pinyins:
        if (not pinyin in candidate_map):
            return None
        k = randint(0, len(candidate_map[pinyin]) - 1)
        predicted = candidate_map[pinyin][k]
        res.append(predicted)
    return res


# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_unigram(pinyin_str, unigram_counts, candidate_map):
    # print("Predicting \"" + pinyin_str + "\" using unigrams")
    pinyins = re.split("\s+", pinyin_str)
    res = []
    for pinyin in pinyins:
        if (not pinyin in candidate_map):
            return None
        predicted = candidate_map[pinyin][0]
        for character in candidate_map[pinyin]:
            cur_pair = format_pair(character, pinyin)
            predicted_pair = format_pair(predicted, pinyin)
            if unigram_counts.get(cur_pair, 0) > unigram_counts.get(predicted_pair, 0):
                predicted = character
        res.append(predicted)
    return res

# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_bigram_dp(pinyin_str, smoother, candidate_map):
    # print("Predicting \"" + pinyin_str + "\" using bigrams")
    pinyins = re.split("\s+", pinyin_str)
    pinyins.insert(0, "<s>")
    pinyins.insert(len(pinyins), "</s>")
    n = len(pinyins)
    # DP array, f[i] is a map from character at i to sum_log_prob up to i
    # dp formula: f(i, cur) = max(f(i-1, prev) + log_cond_prob(prev, cur))
    # goal: maximize sum of log_probabilities
    f = []
    best_prev = []
    for i in range(0, n):
        f.append({})
        best_prev.append({})
    f[0]["<s>"] = log(1.0)

    for i in range(1, n):
        prev_chars = f[i - 1].keys()
        if (not pinyins[i] in candidate_map):
            return None
        for cur_char in candidate_map[pinyins[i]]:
            cur_pair = format_pair(cur_char, pinyins[i])
            f[i][cur_char] = float("-inf")
            best_prev[i][cur_char] = None
            for prev_char in prev_chars:
                prev_pair = format_pair(prev_char, pinyins[i - 1])
                log_prob = smoother.bigram_log_prob(prev_pair, cur_pair)
                if f[i][cur_char] < f[i - 1][prev_char] + log_prob:
                    f[i][cur_char] = f[i - 1][prev_char] + log_prob
                    best_prev[i][cur_char] = prev_char

    # print f
    # trace back the optimal choices
    res = []
    last_char = "</s>"
    for i in reversed(range(2, n)):
        try:
            res.insert(0, best_prev[i][last_char])
            last_char = best_prev[i][last_char]
        except KeyError:
            print pinyin_str
        
    return res            

# model_label: "baseline|unigram|bigram"
def get_accuracy(model_label, bitext_testing, unigram_counts, candidate_map, smoother=None):
    total_chars = 0
    correct_chars = 0
    count = 0
    for segment in bitext_testing:
        count += 1
        if (count % (len(bitext_testing) / 10) == 0):
            print(str(int(round(count * 100.0 / len(bitext_testing)))) + "%")
        pinyins = bitext_segment_to_pinyin_str(segment)
        expected = bitext_segment_to_char_str(segment).split(u" ")
        actual = None
        if model_label == "baseline":
            actual = convert_baseline(pinyins, candidate_map)
        elif model_label == "unigram":
            actual = convert_unigram(pinyins, unigram_counts, candidate_map)
        elif model_label == "bigram":
            actual = convert_bigram_dp(pinyins, smoother, candidate_map)
        if actual == None:
            # print "skipped " + u" ".join(expected)
            continue
        # print(u" ".join(expected))
        # print(u" ".join(actual))
        for i in range(0, len(expected)):
            total_chars += 1
            if actual[i] == expected[i]:
                correct_chars += 1
    return correct_chars * 1.0 / total_chars

if __name__ == "__main__":
    bitext_training = get_bitext_corpus("training")
    candidate_map = init_candidate_map()

    f = open('candidate_map.json','w')
    f.write(json.dumps(candidate_map))
    f.close();

    unigram_counts = get_ngram_counts(bitext_training, 1)

    f = open('unigram_counts.json','w')
    f.write(json.dumps(unigram_counts))
    f.close();

    bigram_counts = get_ngram_counts(bitext_training, 2)

    f = open('bigram_counts.json','w')
    f.write(json.dumps(bigram_counts))
    f.close();

    smoother = smoothing.Laplace(unigram_counts, bigram_counts)
    # smoother = smoothing.GoodTuring(unigram_counts, bigram_counts)
    # smoother = smoothing.WittenBell(unigram_counts, bigram_counts)

    print("training set accuarcy:")
    print("baseline")
    print(get_accuracy("baseline", bitext_training, unigram_counts, candidate_map))
    print("unigram")
    print(get_accuracy("unigram", bitext_training, unigram_counts, candidate_map))

    bitext_testing = get_bitext_corpus("test")

    f = open('test_bitext.json','w')
    f.write(json.dumps(bitext_testing))
    f.close();
    
    print("test set accuarcy:")
    print("baseline")
    print(get_accuracy("baseline", bitext_testing, unigram_counts, candidate_map))
    print("unigram")
    print(get_accuracy("unigram", bitext_testing, unigram_counts, candidate_map))
    print("bigram")
    print(get_accuracy("bigram", bitext_testing, unigram_counts, candidate_map, smoother))
    