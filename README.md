# Pinyin2Chars

Final project for CSE/LING 472.

A simple algorithm that guesses the corresponding Chinese characters for input pinyin text segments.
Based on a bigram model using the LCMC corpus.

## Configuration
- Place a SQlite version of the LCMC corpus at `data/lcmc.db3`. The corpus can be downloaded and ported to SQLite following this guide: http://www.zhtoolkit.com/posts/2012/10/lcmc-as-sql-database/
- Recommended for performance: create indexes on (file_id, sentence_id, word_num, char_num)