import sqlite3

# TRAINING_SET_TEXT_TYPES = '("A")'
# TEST_SET_TEXT_TYPES = '("M")'

TRAINING_SET_TEXT_TYPES = '("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K")'
TEST_SET_TEXT_TYPES = '("L", "M", "N", "P", "R")'

GET_BITEXT = '''
        SELECT c.file_id, c.sentence_id, c.word_num, c.char_num,
            c.character, pc.character
        FROM characters c JOIN pinyin_characters pc
            USING (file_id, sentence_id, word_num, char_num)
        WHERE c.text_id in {}
    '''

GET_NONCHARS = '''
        SELECT c.file_id, c.sentence_id, c.word_num, c.char_num,
            c.character, c.character, c.token_type
        FROM characters c
        WHERE c.text_id in {} and c.is_cjk = "N"
    '''

GET_CANDIDATE_CHARS = '''
        SELECT pc.character, c.character, c.is_cjk
        FROM characters c LEFT OUTER JOIN pinyin_characters pc USING (file_id, sentence_id, word_num, char_num)
        WHERE c.token_type = "w"
        GROUP BY pc.character, c.character
    '''

connection = sqlite3.connect('data/lcmc.db3')
cursor = connection.cursor()

def get_bitext(division):
    if (division == "training"):
        return cursor.execute(GET_BITEXT.format(TRAINING_SET_TEXT_TYPES))
    if (division == "test"):
        return cursor.execute(GET_BITEXT.format(TEST_SET_TEXT_TYPES))

def get_nonchars(division):
    if (division == "training"):
        return cursor.execute(GET_NONCHARS.format(TRAINING_SET_TEXT_TYPES))
    if (division == "test"):
        return cursor.execute(GET_NONCHARS.format(TEST_SET_TEXT_TYPES))

def get_candidate_chars():
    return cursor.execute(GET_CANDIDATE_CHARS)
