#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import copy
import re
import json
import operator

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
    return ngram_counts

# Baseline: randomly pick a candicate character
# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_baseline(pinyin_str, candidate_map, has_tone=True):
    pinyins = re.split("\s+", pinyin_str)
    res = []
    if not has_tone:
        for pinyin_raw in pinyins:
            candidate_chars = set()
            for tone in range(1, 6):
                pinyin = pinyin_raw + str(tone)
                if (not pinyin in candidate_map):
                    continue
                for character in candidate_map[pinyin]:
                    candidate_chars.add(character)
            if (len(candidate_chars) == 0):
                return None
            k = randint(0, len(candidate_chars) - 1)
            predicted = list(candidate_chars)[k]
            res.append(predicted)
        return res
    # has tone
    for pinyin in pinyins:
        if (not pinyin in candidate_map):
            return None
        k = randint(0, len(candidate_map[pinyin]) - 1)
        predicted = candidate_map[pinyin][k]
        res.append(predicted)
    return res

# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_unigram(pinyin_str, unigram_counts, candidate_map, has_tone=True):
    # print("Predicting \"" + pinyin_str + "\" using unigrams")
    pinyins = re.split("\s+", pinyin_str)
    res = []
    if (not has_tone):
        for pinyin_raw in pinyins:
            candidate_chars = {}    
            for tone in range(1, 6):
                pinyin = pinyin_raw + str(tone)
                if (not pinyin in candidate_map):
                    continue
                for character in candidate_map[pinyin]:
                    cur_pair = format_pair(character, pinyin)
                    candidate_chars[character] = candidate_chars.get(character, 0) + unigram_counts.get(cur_pair, 0)
            if (candidate_chars == {}):
                return None
            res.append(max(candidate_chars.iteritems(), key=operator.itemgetter(1))[0])
        return res
    # has tone        
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

def convert_bigram_dp_no_tones(pinyin_str, smoother, candidate_map):
    pinyins = re.split("\s+", pinyin_str)
    pinyins.insert(0, "<s>")
    pinyins.insert(len(pinyins), "</s>")
    n = len(pinyins)
    # DP array, f[i, cur] is a map from character at i to sum_log_prob up to i,
    #   where the last unigram is cur. cur has tones.
    # dp formula: f(i, cur) = max(f(i-1, prev) + log_cond_prob(prev, cur))
    # goal: maximize sum of log_probabilities
    f = []
    best_prev = []
    for i in range(0, n):
        f.append({})
        best_prev.append({})
    f[0]["<s>#<s>"] = log(1.0)

    for i in range(1, n):
        prev_pairs = f[i - 1].keys()  # has tones
        for t in range(1, 6):
            # if (not pinyins[i] in candidate_map):
            #     return None
            pinyin = pinyins[i]
            if (re.match(r"^[a-z]+$", pinyin)):
                pinyin = pinyin + str(t)
            if not pinyin in candidate_map:
                continue
            for cur_char in candidate_map[pinyin]:
                cur_pair = format_pair(cur_char, pinyin)
                f[i][cur_pair] = float("-inf")
                best_prev[i][cur_pair] = None
                for prev_pair in prev_pairs:
                    log_prob = smoother.bigram_log_prob(prev_pair, cur_pair)
                    if f[i][cur_pair] < f[i - 1][prev_pair] + log_prob:
                        f[i][cur_pair] = f[i - 1][prev_pair] + log_prob
                        best_prev[i][cur_pair] = prev_pair
            if (pinyin == pinyins[i]): # special chars
                break
    # print f
    # trace back the optimal choices
    res = []
    last_pair = "</s>#</s>"
    for i in reversed(range(2, n)):
        try:
            res.insert(0, best_prev[i][last_pair].split(u"#")[0])
            last_pair = best_prev[i][last_pair]
        except AttributeError:
            print pinyin_str
    return res            

# pinyin_str: string of pinyin tokens, no start/end symbol
# returns a list of predicted characters
def convert_bigram_dp(pinyin_str, smoother, candidate_map, has_tone=True):
    if (not has_tone):
        return convert_bigram_dp_no_tones(pinyin_str, smoother, candidate_map)
    # print("Predicting \"" + pinyin_str + "\" using bigrams")
    pinyins = re.split("\s+", pinyin_str)
    pinyins.insert(0, "<s>")
    pinyins.insert(len(pinyins), "</s>")
    n = len(pinyins)
    # DP array, f[i, cur] is a map from character at i to sum_log_prob up to i,
    #   where the last unigram is cur
    # dp formula: f(i, cur) = max(f(i-1, prev) + log_cond_prob(prev, cur))
    # goal: maximize sum of log_probabilities
    f = []
    best_prev = []
    for i in range(0, n):
        f.append({})
        best_prev.append({})
    f[0]["<s>#<s>"] = log(1.0)

    for i in range(1, n):
        prev_pairs = f[i - 1].keys()
        if (not pinyins[i] in candidate_map):
            return None
        for cur_char in candidate_map[pinyins[i]]:
            cur_pair = format_pair(cur_char, pinyins[i])
            f[i][cur_pair] = float("-inf")
            best_prev[i][cur_pair] = None
            for prev_pair in prev_pairs:
                log_prob = smoother.bigram_log_prob(prev_pair, cur_pair)
                if f[i][cur_pair] < f[i - 1][prev_pair] + log_prob:
                    f[i][cur_pair] = f[i - 1][prev_pair] + log_prob
                    best_prev[i][cur_pair] = prev_pair
    # print f
    # trace back the optimal choices
    res = []
    last_pair = "</s>#</s>"
    for i in reversed(range(2, n)):
        try:
            res.insert(0, best_prev[i][last_pair].split("#")[0])
            last_pair = best_prev[i][last_pair]
        except KeyError:
            print pinyin_str
    return res            

# model_label: "baseline|unigram|bigram"
def get_accuracy(model_label, bitext_testing, unigram_counts, candidate_map, smoother=None, has_tone=True):
    total_chars = 0
    correct_chars = 0
    count = 0
    for segment in bitext_testing:
        count += 1
        if (count % (len(bitext_testing) / 10) == 0):
            print(str(int(round(count * 100.0 / len(bitext_testing)))) + "%")
        pinyins = bitext_segment_to_pinyin_str(segment)
        if (not has_tone):
            pinyins = re.sub(r"\d", "", pinyins)
        expected = bitext_segment_to_char_str(segment).split(u" ")
        actual = None
        if model_label == "baseline":
            actual = convert_baseline(pinyins, candidate_map, has_tone)
        elif model_label == "unigram":
            actual = convert_unigram(pinyins, unigram_counts, candidate_map, has_tone)
        elif model_label == "bigram":
            actual = convert_bigram_dp(pinyins, smoother, candidate_map, has_tone)
        if actual == None or len(actual) != len(expected):
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

    #Good turing smoothing initialization takes longer. Precomputes it now.
    print("Intializing smoothing...")
    smoother = smoothing.GoodTuring(unigram_counts, bigram_counts)
    f = open('gt_smoothed_counts.json','w')
    f.write(json.dumps(smoother.smoothed_uc))
    f.close();

    has_tone = True
    # has_tone = False
    smoother = smoothing.Laplace(unigram_counts, bigram_counts)
    # smoother = smoothing.GoodTuring(unigram_counts, bigram_counts)
    # smoother = smoothing.WittenBell(unigram_counts, bigram_counts)

    print("training set accuarcy:")
    print("baseline")
    print(get_accuracy("baseline", bitext_training, unigram_counts, candidate_map, smoother, has_tone))
    print("unigram")
    print(get_accuracy("unigram", bitext_training, unigram_counts, candidate_map, smoother, has_tone))

    bitext_testing = get_bitext_corpus("test")

    f = open('test_bitext.json','w')
    f.write(json.dumps(bitext_testing))
    f.close();
    
    print("test set accuarcy:")
    print("baseline")
    print(get_accuracy("baseline", bitext_testing, unigram_counts, candidate_map, smoother, has_tone))
    print("unigram")
    print(get_accuracy("unigram", bitext_testing, unigram_counts, candidate_map, smoother, has_tone))
    print("bigram")
    print(get_accuracy("bigram", bitext_testing, unigram_counts, candidate_map, smoother, has_tone))
