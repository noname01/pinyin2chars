# Pinyin2Chars

Final project for CSE/LING 472.

A simple algorithm that guesses the corresponding Chinese characters for input pinyin text segments.
Based on an n-gram model using the LCMC corpus. Developed under python 2.7.11.

## Web Demo
The web demo is running at https://pinyins2chars.herokuapp.com/. We recommend using this for grading purposes, since we already configured the database, and the test sets generated are relative small to be able to finish in reasonable amount of time.

## Guide to run the code
- Unzip the lcmc.zip in /data. Make sure the file lcmc.db3 is under /data. This database file can be downloaded from https://drive.google.com/file/d/0B6AoAA-0CimLTXMzRzNsdzltWVE/view.
- To run the server locally, run `python server.py`. You can then point your browser to localhost:5000 to see the web ui. (Note that the server needs language model json files. Make sure they exit in the project root.)
- To train the language models, run `pythin pinyin2chars.py`. This will generate new language model json files, and output accuracy information to stdout. Change the corresponding lines in main() of `pinyin2chars.py` and `sqlqueries.py` to test for different configurations. **Warning: this may take a long time!**
- Have fun playing with our model!