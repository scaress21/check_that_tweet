import numpy as np
import pandas as pd
import pickle
import time
from tweetscrape.search_tweets import TweetScrapperSearch
from tweetscrape.users_scrape import TweetScrapperUser
from flask import Flask, request, Response, render_template, jsonify

#Initial function to get tweets based on keyword, date, location, and number
def get_tweets(word, date, number):

    #gather the tweets and export to a csv
    tweet_scrapper = TweetScrapperSearch(search_all = word, search_till_date= date, num_tweets=number, tweet_dump_path=f'./data/{date}_{word}_tweets.csv', tweet_dump_format='csv')
    tweet_count, tweet_id, tweet_time, dump_path = tweet_scrapper.get_search_tweets()

    #read the csv back in as a dataframe
    tweets = pd.read_csv(f'./data/{date}_{word}_tweets.csv')
    tweets = tweets.drop_duplicates()

    tweets = tweets.reset_index()

    return tweets

#Second function that goes back through the dataframe to get user info in separate pull
def get_user(df):
    count = 0
    df['user_bio'] = 0
    df['user_location'] = 0
    df['user_url'] = 0
    df['user_tweets'] = 0
    df['user_following'] = 0
    df['user_followers'] = 0
    df['user_favorites'] = 0
    for user in df['author']:
        count += 1
        try:
            ts = TweetScrapperUser(user)
            user_info = ts.get_profile_info()
            df.loc[df['author'] == user, 'user_bio'] = user_info['bio']
            df.loc[df['author'] == user,'user_location'] = user_info['location']
            df.loc[df['author'] == user,'user_url'] = user_info['url']
            df.loc[df['author'] == user,'user_tweets'] = user_info['tweets']
            df.loc[df['author'] == user,'user_following'] = user_info['following']
            df.loc[df['author'] == user,'user_followers'] = user_info['followers']
            df.loc[df['author'] == user,'user_favorites'] = user_info['favorites']

        except:
            pass
    df.to_csv(f'./data/tweets_users.csv', index=False)
    return df
#A few helpful functions that help format the data
def get_ratio(followers, following):
    if following == 0:
        following = 1
    elif followers == 0:
        return 0
    else:
        return round(int(followers) / int(following), 2)
def make_url(author, idd):
    return f'https://twitter.com/{author}/status/{idd}'

def change_time(x):
    x = x / 1000
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(x))

def to_check(x):
    if (x == 0) or (x == 3) or (x == 2):
        return 'Check this tweet!'
    else:
        return 'Not a priority.'

#Next function takes the data, runs it through the model, and outputs which tweets to check
def find_clusters(df):
    knn = pickle.load(open('./models/knn.pkl', 'rb'))
    ss = pickle.load(open('./models/standardscaler.pkl', 'rb'))

    df['has_bio'] = df['user_bio'].notna().astype(int)
    df['has_location'] = df['user_bio'].notna().astype(int)
    df['has_url'] = df['user_bio'].notna().astype(int)
    df['ratio'] = [get_ratio(m, n) for m, n in zip(df['user_followers'], df['user_following'])]

    to_cluster = df[['user_tweets', 'user_following', 'user_followers',
             'ratio', 'has_url', 'has_location', 'has_bio']]

    to_cluster = to_cluster.fillna(0)
    z_cluster = ss.transform(to_cluster)
    df['groups'] = knn.predict(z_cluster)

    df['to_check'] = df['groups'].apply(to_check)

    df['time'] = df['time'].apply(change_time)
    df['tweet_url'] = [make_url(author, idd) for author, idd in zip(df['author'], df['id'])]

    df = df.sort_values('to_check')
    df.index = np.arange(1, len(df) + 1)

    df.columns = [x.replace("_", ' ').title() for x in list(df.columns)]

    columns = ['Time', 'Author', 'Text', 'Reply Count', 'Favorite Count', 'Retweet Count', 'Tweet Url', 'User Followers', 'User Following', 'Groups','To Check']


    return df[columns]

#Last function to put all the pieces together!
def put_it_together(word, date, number):
    tweets = get_tweets(word, date, number)
    users = get_user(tweets)
    to_check = find_clusters(users)
    return to_check

app = Flask('myApp')

@app.route('/')

def form():
    return render_template('form.html')

@app.route('/submit')

def submit():
    user_input = request.args

    df = put_it_together(user_input['word'],user_input['date'], int(user_input['number']))
    return render_template('results.html', table = df.to_html())

if __name__ == '__main__':
    app.run(debug = True)
