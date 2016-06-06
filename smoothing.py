from math import log

class Laplace(object):
    def __init__(self, unigram_counts, bigram_counts):
        self.unigram_counts = unigram_counts
        self.bigram_counts = bigram_counts
        self.zgc = 0
        for wi in self.unigram_counts.keys():
            self.zgc += self.unigram_counts[wi]        
    
    def bigram_prob(self, w1, w2):
        bc = self.bigram_counts.get(w1 + u" " + w2, 0) + 1
        uc = self.unigram_counts.get(w1, 0) + len(self.unigram_counts.keys())
        return bc * 1.0 / uc

    def bigram_log_prob(self, w1, w2):
        return log(self.bigram_prob(w1, w2))
    

class WittenBell(object):
    def __init__(self, unigram_counts, bigram_counts):
        self.unigram_counts = unigram_counts
        self.bigram_counts = bigram_counts
        self.w1map = dict()
        for bigram in bigram_counts.keys():
            tokens = bigram.split(" ")
            if len(tokens) > 1:
                if not tokens[0] in self.w1map:
                    self.w1map[tokens[0]] = set()
                self.w1map[tokens[0]].add(tokens[1])

    def bigram_prob(self, w1, w2):
        bigram = w1 + u" " + w2
        T = len(self.w1map.get(w1, [])) + 0.1**50 # a hack to avoid division by zero
        Z = len(self.unigram_counts.keys()) - T
        bc = self.bigram_counts.get(bigram, 0) 
        if (bc > 0):
            return bc * 1.0 / (self.unigram_counts.get(w1, 0) + T)
        if (self.unigram_counts.get(w1, 0) + T == 0):
            return 0.0
        return T * 1.0 /  (Z * (self.unigram_counts.get(w1, 0) + T))
    
    def bigram_log_prob(self, w1, w2):
        prob = self.bigram_prob(w1, w2)
        return log(prob)

class GoodTuring(object):
    def __init__(self, unigram_counts, bigram_counts):
        self.unigram_counts = unigram_counts
        self.bigram_counts = bigram_counts
        self.smoothed_bc = {}
        self.smoothed_uc = {}
        self.N = {}
        self.N_tot = 0
        # Only do discount up to c = k
        K = 5
        N = self.N
        for bigram in bigram_counts.keys():
            c = self.bigram_counts[bigram]
            self.N_tot += c
            self.N[c] = self.N.get(c, 0) + 1

        for bigram in bigram_counts.keys():
            c = self.bigram_counts[bigram] * 1.0
            if c <= K:
                c = ((c + 1) * N[c + 1] * 1.0 / N[c] - \
                    c * (K + 1) * N[K + 1] * 1.0 / N[1]) / \
                    (1 - (K + 1) * N[K + 1] * 1.0 / N[1])
            self.smoothed_bc[bigram] = c

        unigrams = list(unigram_counts.keys())
        print(len(unigrams))
        for wi in unigrams:
            uc = 0
            for wj in unigrams:
                uc += self.bigram_count(wi, wj)
            self.smoothed_uc[wi] = uc

    def bigram_count(self, w1, w2):
        bigram = w1 + u" " + w2
        bc = self.smoothed_bc.get(bigram, 0)
        if (bc == 0):
            bc = self.N[1] * 1.0 / self.N_tot
        return bc

    def bigram_prob(self, w1, w2):
        bc = self.bigram_count(w1, w2)
        if (w1 in self.unigram_counts):
            uc = self.smoothed_uc[w1]
        else:
            uc = self.N[1] * 1.0 / self.N_tot * len(self.unigram_counts.keys())
        return bc * 1.0 / uc

    def bigram_log_prob(self, w1, w2):
        return log(self.bigram_prob(w1, w2))
