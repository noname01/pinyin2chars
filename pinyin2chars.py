#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import copy
import re
from math import log

import sqlqueries

def cid_to_sid(cid):
    return cid[:cid.index("-")]

def format_cid(ids):
    word_num = str(ids[2]).zfill(3)
    char_num = str(ids[3]).zfill(2)
    return "{}.{}-{}:{}".format(str(ids[0]), str(ids[1]), word_num, char_num)

def format_pair(character, pinyin):
    return character + u"#" + pinyin

# Bitext: list(list(str)), a list of text segments / utterances.
# Each str has the form: "char#pinyin", or "x#x" where is_cjk of x = "N"
def get_bitext_corpus():
    print("Loading bitext...")
    # Query returns a list of tuples (cid, "char#pinyin"). Punctuations excluded.
    # cid = "file_id.sentence_id.word_num.char_num"
    cid_map = {}
    training_chars = set()
    for tup in sqlqueries.get_bitext():
        cid_map[format_cid(tup[0:4])] = format_pair(tup[4], tup[5])
        training_chars.add(tup[4])
    # Query returns non-cjk chars. The value is "x#x".
    nonchar_cids = set()
    
    for tup in sqlqueries.get_nonchars():
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
    # print u" ".join(training_chars)
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
        if (not tup[0] in res):
            res[tup[0]] = []
        res[tup[0]].append(tup[1])
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

# Laplace for now.
# Returns a real number.
def get_smoothed_count(gram, raw_count_map):
    return raw_count_map.get(gram, 0) + 1.0

def get_cond_prob_bigram(w1, w2, unigram_counts, bigram_counts):
    return get_smoothed_count(w1 + u" " + w2, bigram_counts) / get_smoothed_count(w1, unigram_counts)

def get_log_cond_prob_bigram(w1, w2, unigram_counts, bigram_counts):
    return log(get_cond_prob_bigram(w1, w2, unigram_counts, bigram_counts))

# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_unigram(pinyin_str, unigram_counts, candidate_map):
    pinyins = re.split("\s+", pinyin_str)
    res = []
    for pinyin in pinyins:
        if (not pinyin in candidate_map):
            return None
        predicted = candidate_map[pinyin][0]
        for character in candidate_map[pinyin]:
            cur_pair = format_pair(character, pinyin)
            predicted_pair = format_pair(predicted, pinyin)
            if get_smoothed_count(cur_pair, unigram_counts) > get_smoothed_count(predicted_pair, unigram_counts):
                predicted = character
        res.append(predicted)
    return res

# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_bigram_dp(pinyin_str, unigram_counts, bigram_counts, candidate_map):
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
                log_prob = get_log_cond_prob_bigram(prev_pair, cur_pair, unigram_counts, bigram_counts)
                if f[i][cur_char] < f[i - 1][prev_char] + log_prob:
                    f[i][cur_char] = f[i - 1][prev_char] + log_prob
                    best_prev[i][cur_char] = prev_char
        print(f[i])
    res = []
    last_char = "</s>"
    i = n - 1
    while i > 0:
        res.insert(0, best_prev[i][last_char])
        last_char = best_prev[i][last_char]
        i -= 1
    return res            

bitext = get_bitext_corpus()
candidate_map = init_candidate_map()

unigram_counts = get_ngram_counts(bitext, 1)
bigram_counts = get_ngram_counts(bitext, 2)

chars = convert_unigram("jin1 tian1 tian1 qi4 hen3 hao3 a5", unigram_counts, candidate_map)
print(u" ".join(chars))

chars = convert_bigram_dp("jin1 tian1 tian1 qi4 hen3 hao3 a5", unigram_counts, bigram_counts, candidate_map)
print(u" ".join(chars))

chars = convert_bigram_dp("xue2 xiao4", unigram_counts, bigram_counts, candidate_map)
print(u" ".join(chars))

# algorithm should be correct but smoothing has problems...