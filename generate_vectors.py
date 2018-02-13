#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import os
import time
from multiprocessing import cpu_count

import tinysegmenter
import wget
from gensim.corpora import WikiCorpus
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--mecab', action='store_true')

args = parser.parse_args()
USE_MECAB_TOKENIZER = args.mecab is not None

if USE_MECAB_TOKENIZER:
    logging.info('Using the MeCab tokenizer. Installation procedure is ' +
                 'provided at http://www.robfahey.co.uk/blog/japanese-text-analysis-in-python/')
    import MeCab
else:
    logging.info('Using the tinysegmenter tokenizer. Its not very accurate. ' +
                 'Consider using MeCab instead with option --mecab.')

VECTORS_SIZE = 50
INPUT_FILENAME = 'jawiki-latest-pages-articles.xml.bz2'

JA_WIKI_TEXT_FILENAME = 'jawiki-latest-text.txt'
JA_WIKI_SENTENCES_FILENAME = 'jawiki-latest-text-sentences.txt'

JA_WIKI_TEXT_TOKENS_FILENAME = 'jawiki-latest-text-tokens.txt'
JA_WIKI_SENTENCES_TOKENS_FILENAME = 'jawiki-latest-text-sentences-tokens.txt'

JA_VECTORS_MODEL_FILENAME = 'ja-gensim.{}d.data.model'.format(VECTORS_SIZE)
JA_VECTORS_TEXT_FILENAME = 'ja-gensim.{}d.data.txt'.format(VECTORS_SIZE)
JA_WIKI_LATEST_URL = 'https://dumps.wikimedia.org/jawiki/latest/jawiki-latest-pages-articles.xml.bz2'


# CHECK WHERE THE HECK ARE THE PUNCTUATIONS GONE. Okay it's in get_text()
# WHY WE DO NOT HAVE ANY OUTPUT ON WORD2VEC. We have to define a logging interface

def generate_vectors(input_filename, output_filename, output_filename_2):
    if os.path.isfile(output_filename):
        logging.info('Skipping generate_vectors(). File already exists: {}'.format(output_filename))
        return
    start = time.time()
    model = Word2Vec(LineSentence(input_filename),
                     size=VECTORS_SIZE, window=5, min_count=5,
                     workers=cpu_count(), iter=5)
    model.save(output_filename)
    model.wv.save_word2vec_format(output_filename_2, binary=False)
    logging.info('Finished generate_vectors(). It took {0:.2f} s to execute.'.format(round(time.time() - start, 2)))


def get_words(text):
    import MeCab
    mt = MeCab.Tagger("-d /usr/local/lib/mecab/dic/mecab-ipadic-neologd")
    mt.parse("")
    parsed = mt.parseToNode(text)
    components = []
    while parsed:
        components.append(parsed.surface)
        parsed = parsed.next
    return components


def tokenize_text(input_filename, output_filename):
    if os.path.isfile(output_filename):
        logging.info('Skipping tokenize_text(). File already exists: {}'.format(output_filename))
        return
    start = time.time()
    with open(output_filename, 'wb') as out:
        with open(input_filename, 'rb') as inp:
            for i, text in enumerate(inp.readlines()):
                if USE_MECAB_TOKENIZER:
                    tokenized_text = ' '.join(get_words(text.decode('utf8')))
                else:
                    tokenized_text = ' '.join(tinysegmenter.tokenize(text.decode('utf8')))
                out.write(tokenized_text.encode('utf8'))
                if i % 100 == 0 and i != 0:
                    logging.info('Tokenized {} articles.'.format(i))
    logging.info('Finished tokenize_text(). It took {0:.2f} s to execute.'.format(round(time.time() - start, 2)))


def process_wiki_to_text(input_filename, output_text_filename, output_sentences_filename):
    if os.path.isfile(output_text_filename) and os.path.isfile(output_sentences_filename):
        logging.info('Skipping process_wiki_to_text(). Files already exist: {} {}'.format(output_text_filename,
                                                                                          output_sentences_filename))
        return
    start = time.time()
    intermediary_time = None
    sentences_count = 0
    with open(output_text_filename, 'wb') as out:
        with open(output_sentences_filename, 'wb') as out_sentences:
            wiki = WikiCorpus(input_filename, lemmatize=False, dictionary={}, processes=cpu_count())
            wiki.metadata = True
            texts = wiki.get_texts()
            for i, article in enumerate(texts):
                text_list = article[0]  # article[1] refers to the name of the article.
                sentences = text_list
                # re.search('[a-zA-Z]+', string) maybe add it
                sentences_count += len(sentences)
                for sentence in sentences:
                    out_sentences.write((sentence + b'\n'))
                text = b' '.join(sentences) + b'\n'
                out.write(text)
                if i % (100 - 1) == 0 and i != 0:
                    if intermediary_time is None:
                        intermediary_time = time.time()
                        elapsed = intermediary_time - start
                    else:
                        new_time = time.time()
                        elapsed = new_time - intermediary_time
                        intermediary_time = new_time
                    sentences_per_sec = int(len(sentences) / elapsed)
                    logging.info('Saved {0} articles containing {1} sentences ({2} sentences/sec).'.format(i + 1,
                                                                                                           sentences_count,
                                                                                                           sentences_per_sec))
        logging.info(
            'Finished process_wiki_to_text(). It took {0:.2f} s to execute.'.format(round(time.time() - start, 2)))


if __name__ == '__main__':
    if not os.path.isfile(INPUT_FILENAME):
        wget.download(JA_WIKI_LATEST_URL)

    process_wiki_to_text(INPUT_FILENAME, JA_WIKI_TEXT_FILENAME, JA_WIKI_SENTENCES_FILENAME)
    tokenize_text(JA_WIKI_TEXT_FILENAME, JA_WIKI_TEXT_TOKENS_FILENAME)

    # Useful for sentences to vec (skip thought vectors) but not for word2vec.
    # tokenize_text(JA_WIKI_SENTENCES_FILENAME, JA_WIKI_SENTENCES_TOKENS_FILENAME)

    generate_vectors(JA_WIKI_TEXT_TOKENS_FILENAME, JA_VECTORS_MODEL_FILENAME, JA_VECTORS_TEXT_FILENAME)
