import sqlite3

import sqlqueries

connection = sqlite3.connect('data/lcmc.db3')
cursor = connection.cursor()

# bitext: list(list(str)), a list of sentences. Each str has the form: "char#pinyin"
def get_bitext_corpus():
    cursor.execute(sqlqueries.GET_BITEXT_QUERY)
    raw_res = cursor.fetchall()
    return raw_res

bitext = get_bitext_corpus()

print bitext

