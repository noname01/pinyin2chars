# hardcoded text type for now

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
