import sqlite3

# hardcoded text type for now
# TODO: create a table for candidate chars

GET_BITEXT = '''
        SELECT c.file_id, c.sentence_id, c.word_num, c.char_num,
            c.character, pc.character
        FROM characters c JOIN pinyin_characters pc
            USING (file_id, sentence_id, word_num, char_num)
        WHERE c.text_id in ("M")
    '''

GET_NONCHARS = '''
        SELECT c.file_id, c.sentence_id, c.word_num, c.char_num,
            c.character, c.character, c.token_type
        FROM characters c
        WHERE c.text_id in ("M") and c.is_cjk = "N"
    '''

GET_CANDIDATE_CHARS = '''
        SELECT DISTINCT pc.character, c.character
        FROM characters c JOIN pinyin_characters pc USING (file_id, sentence_id, word_num, char_num)
        WHERE c.is_cjk = "Y"
    '''

connection = sqlite3.connect('data/lcmc.db3')
cursor = connection.cursor()

def get_bitext():
    return cursor.execute(GET_BITEXT)

def get_nonchars():
    return cursor.execute(GET_NONCHARS)

def get_candidate_chars():
    return cursor.execute(GET_CANDIDATE_CHARS)
