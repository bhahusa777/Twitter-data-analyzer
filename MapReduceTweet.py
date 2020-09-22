import tweepy
from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import json
import pandas as pd
import csv
from csv import DictReader
from collections import Counter

import re
from textblob import TextBlob
import string
import preprocessor as p

from concurrent.futures import ThreadPoolExecutor
import time
import nltk

from functools import reduce
from multiprocessing import Pool
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize



import os


csv_file_name = "/Users/Lionel777/PythonLearning/CouldProject/Covid.csv"
key_words = "#corona or #virus or #covid-19"
consumer_key = "l8vceSKgQF8qQvUNttZZovRgM"
consumer_secret = "GwqtLTtQRFTtTkpBomQcldSz7jAZcd2vI0SxfP2iP0IlzUXwKI"

access_token = "1260598633784721409-Tcfh1GFMIKMSlR3mYnm05CMWZbsyYV"

access_token_secret = "sCFCB984wE8XgehbYjCa14E2n7TPJ6Zv4Iea64IGfpWTy"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

COLMS = ['id', 'created_at', 'source', 'original_text','clean_text', 'sentiment','polarity','subjectivity', 'lang',
'favorite_count', 'retweet_count', 'original_author',   'possibly_sensitive', 'hashtags', 'place']

#Happy Emoticons

happy_set = set([
    ':-)', ':)', ';)', ':o)', ':]', ':3', ':c)', ':>', '=]', '8)', '=)', ':}',
    ':^)', ':-D', ':D', '8-D', '8D', 'x-D', 'xD', 'X-D', 'XD', '=-D', '=D',
    '=-3', '=3', ':-))', ":'-)", ":')", ':*', ':^*', '>:P', ':-P', ':P', 'X-P',
    'x-p', 'xp', 'XP', ':-p', ':p', '=p', ':-b', ':b', '>:)', '>;)', '>:-)',
    '<3'
    ])

sad_set = set([
    ':L', ':-/', '>:/', ':S', '>:[', ':@', ':-(', ':[', ':-||', '=L', ':<',
    ':-[', ':-<', '=\\', '=/', '>:(', ':(', '>.<', ":'-(", ":'(", ':\\', ':-c',
    ':c', ':{', '>:\\', ';('
    ])

#Emoji patterns
emoji = re.compile("["
         u"\U0001F600-\U0001F64F"  # emoticons
         u"\U0001F300-\U0001F5FF"  # symbols & pictographs
         u"\U0001F680-\U0001F6FF"  # transport & map symbols
         u"\U0001F1E0-\U0001F1FF"  # flags
         u"\U00002702-\U000027B0"
         u"\U000024C2-\U0001F251"
         "]+", flags=re.UNICODE)

emoticons = happy_set.union(sad_set)


def clean_tweets(tweet):
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(tweet)
    # after tweepy preprocessing the colon symbol left remain after      #removing mentions
    tweet = re.sub(r':', '', tweet)
    tweet = re.sub(r'‚Ä¶', '', tweet)
    tweet = re.sub(r'‚Äô', '', tweet)
    tweet = re.sub(r'...', '', tweet)
    # replace consecutive non-ASCII characters with a space
    tweet = re.sub(r'[^\x00-\x7F]+', ' ', tweet)
    # remove emojis from tweet

    tweet = emoji.sub(r'', tweet)

    # filter using NLTK library append it to a string
    filtered_tweet = [w for w in word_tokens if not w in stop_words]
    filtered_tweet = []
    # looping through conditions
    for w in word_tokens:
        # check tokens against stop words , emoticons and punctuations
        if w not in stop_words and w not in emoticons and w not in string.punctuation:
            filtered_tweet.append(w)
    return ' '.join(filtered_tweet)
    # print(word_tokens)
    # print(filtered_sentence)return tweet
start_date = "2020-04-01"
def write_tweets(keyword, file):
    # If the file exists, then read the existing data from the CSV file.
    if os.path.exists(file):
        df = pd.read_csv(file, header=0)
    else:
        df = pd.DataFrame(columns=COLMS)
    #page attribute in tweepy.cursor and iteration
    for page in tweepy.Cursor(api.search, q=keyword,
                              count=200, include_rts=False, since=start_date).pages(100):
        for status in page:
            new_entry = []
            status = status._json

            ## check whether the tweet is in english or skip to the next tweet
            if status['lang'] != 'en':
                continue

            #when run the code, below code replaces the retweet amount and
            #no of favorires that are changed since last download.
            if status['created_at'] in df['created_at'].values:
                i = df.loc[df['created_at'] == status['created_at']].index[0]
                if status['favorite_count'] != df.at[i, 'favorite_count'] or \
                   status['retweet_count'] != df.at[i, 'retweet_count']:
                    df.at[i, 'favorite_count'] = status['favorite_count']
                    df.at[i, 'retweet_count'] = status['retweet_count']
                continue


           #tweepy preprocessing called for basic preprocessing
            clean_text = p.clean(status['text'])

            #call clean_tweet method for extra preprocessing
            filtered_tweet=clean_tweets(clean_text)

            #pass textBlob method for sentiment calculations
            blob = TextBlob(filtered_tweet)
            Sentiment = blob.sentiment

            #seperate polarity and subjectivity in to two variables
            polarity = Sentiment.polarity
            subjectivity = Sentiment.subjectivity

            #new entry append
            new_entry += [status['id'], status['created_at'],
                          status['source'], status['text'],filtered_tweet, Sentiment,polarity,subjectivity, status['lang'],
                          status['favorite_count'], status['retweet_count']]

            #to append original author of the tweet
            new_entry.append(status['user']['screen_name'])

            try:
                is_sensitive = status['possibly_sensitive']
            except KeyError:
                is_sensitive = None
            new_entry.append(is_sensitive)

            # hashtagas and mentiones are saved using comma separted
            hashtags = ", ".join([hashtag_item['text'] for hashtag_item in status['entities']['hashtags']])
            new_entry.append(hashtags)
            # mentions = ", ".join([mention['screen_name'] for mention in status['entities']['user_mentions']])
            # new_entry.append(mentions)

            #get location of the tweet if possible
            try:
                location = status['user']['location']
            except TypeError:
                location = ''
            new_entry.append(location)

            # try:
            #     coordinates = [coord for loc in status['place']['bounding_box']['coordinates'] for coord in loc]
            # except TypeError:
            #     coordinates = None
            # new_entry.append(coordinates)

            single_tweet_df = pd.DataFrame([new_entry], columns=COLMS)
            df = df.append(single_tweet_df, ignore_index=True)
            csvFile = open(file, 'a' ,encoding='utf-8')
            df.to_csv(csvFile, mode='a', columns=COLMS, index=False, encoding="utf-8")


write_tweets(key_words,csv_file_name)
list_words = []

stop_words = set(stopwords.words('english'))

def clean_word(word):
    return re.sub(r'[^\w\s]','',word).lower()

def word_not_in_stopwords(word):
    return word not in stop_words and word and word.isalpha()

with open('Covid.csv', 'r') as read_obj:
    # pass the file object to DictReader() to get the DictReader object
    csv_dict_reader = DictReader(read_obj)
    # get column names from a csv file
    for row in csv_dict_reader:
        list_temp=[]
        list_temp.append(row['clean_text'])
        list_words.extend(list_temp)

def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


data_chunks = list(divide_chunks(list_words, 30))
mapped=[]
def mapper(text):
    list_temp= text.split()
    list_temp = list(map(clean_word, list_temp))
    list_temp = list(filter(word_not_in_stopwords, list_temp))
    return Counter(list_temp)

def reducer(cnt1, cnt2):
    cnt1.update(cnt2)
    return cnt1

def chunk_mapper(chunk):
    mapped = map(mapper, chunk)
    reduced = reduce(reducer, mapped)
    return reduced
def wrap(l):
    p = Pool(l)
    return p.map(chunk_mapper, data_chunks)


with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(wrap,8)
    while True:
        if(future.done()):
            mapped =future.result()
            break
reduced = reduce(reducer, mapped)
print(reduced.most_common(10))