
GET_BITEXT_QUERY = '''SELECT c.file_id || "." || c.sentence_id, c.character,  pc.character
    FROM characters c JOIN pinyin_characters pc USING (file_id, sentence_id, word_num, char_num)
    WHERE c.text_id in ("M")'''

