#!/usr/bin/env python
#
# maintainer @vando
# https://github.com/vando/rss2tw

import argparse
import feedparser
import re
import sqlite3
import tweepy

def ifnotexists(db, cursor):
    try:
        cursor.execute('''SELECT id FROM acct LIMIT 1''')
    except sqlite3.OperationalError:
        cursor.executescript('''
               CREATE TABLE IF NOT EXISTS acct(id INTEGER PRIMARY KEY, name TEXT unique, url TEXT, user TEXT, consumer_key TEXT, consumer_secret TEXT, token_key TEXT, token_secret TEXT);
               CREATE TABLE IF NOT EXISTS feed(id INTEGER PRIMARY KEY, name TEXT unique, url TEXT, inuse TEXT);
               ''')
        db.commit()
        print 'Created tables\n'

def init(name, db, cursor):
    """
    Get access tokens
    """
    url  = raw_input('Feed\'s URL: ').strip()
    consumer_key = raw_input('Consumer key: ').strip()
    consumer_secret = raw_input('Consumer secret: ').strip()
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    try:
        print 'Open the URL in your browser:\n\n\t' + auth.get_authorization_url() + '\n'
    except tweepy.TweepError:
        print 'Error: Failed to get request token.'
        db.close()
        quit(1)
    pin = raw_input('Verification pin number from twitter.com: ').strip()
    try:
        auth.get_access_token(verifier=pin)
    except tweepy.TweepError:
        print 'Error: Failed to get access token.'
        db.close()
        quit(1)
    auth.set_access_token(auth.access_token, auth.access_token_secret)
    api = tweepy.API(auth)
    user = api.me()
    """
    Save it
    """
    try:
        cursor.execute('''INSERT INTO acct(name, url, user, consumer_key, consumer_secret, token_key, token_secret) VALUES (?,?,?,?,?,?,?)''', (name, url, user.screen_name, consumer_key, consumer_secret, auth.access_token, auth.access_token_secret))
    except sqlite3.IntegrityError:
        print 'Duplicated feed name'
    else:
        cursor.execute('''INSERT INTO feed(name, inuse) VALUES(?,?)''', (name, 'NO'))
        db.commit()
    finally:
        db.close()
        print 'Feed was successfully added to database!' 

def list(db, cursor):
    cursor.execute('''SELECT id FROM acct LIMIT 1''')
    if cursor.fetchone() is None:
        print 'Table is empty'
    else:
        cursor.execute('''SELECT * FROM acct ORDER BY id ASC''')
        for row in cursor:
            print('{0} (@{1}): {2}'.format(row[1], row[3], row[2]))
    db.close()

def stus(name, db, cursor):
    if name is None:
        cursor.execute('''SELECT * FROM feed ORDER BY id ASC''')
        for row in cursor:
            print('[{0}] IN USE: {1}, LAST FEED: {2}'.format(row[1], row[3], row[2]))
    else:
        cursor.execute('''SELECT * FROM feed WHERE name=?''', (name,))
        feed = cursor.fetchone()
        if feed:
            print('[{0}] IN USE: {1}, LAST FEED: {2}'.format(row[1], row[3], row[2]))
    db.close()

def post(name, api, title, link, db, cursor):
    """
    (if required) short tweet
    """
    if len(title) > 257:
        tweet = re.sub(' [^ ]*$', '... ', title[0:250]) + link
    else:
        tweet = title + ' ' + link
    """
    post it
    """
    try:
        api.update_status(status=tweet)
    except tweepy.TweepError:
        db.close()
        quit(1)
    else:
        cursor.execute('''UPDATE feed SET url=? WHERE name=?''', (link, name))
        db.commit()

def down(name, db, cursor):
    """
    auth
    """
    cursor.execute('''SELECT consumer_key, consumer_secret, token_key, token_secret FROM acct WHERE name=?''', (name,))
    keys = cursor.fetchone()
    if keys is None:
        print 'Name is invalid'
        db.close()
        quit(1)
    else:
        auth = tweepy.OAuthHandler(keys[0], keys[1])
        auth.set_access_token(keys[2], keys[3])
        api = tweepy.API(auth)
    """
    feedparser 
    """
    cursor.execute('''SELECT url FROM acct WHERE name=?''', (name,))
    furl = cursor.fetchone()
    feed = feedparser.parse(furl[0])
    if feed.status != 200 or not feed.entries:
        quit(1)
    """
    last feed
    """
    cursor.execute('''SELECT url FROM feed WHERE name=?''', (name,))
    last = cursor.fetchone()
    """
    do the magic
    """
    if last is None:
        post(name, api, feed.entries[0].title, feed.entries[0].link, db, cursor)
    else:
        for i in range(len(feed.entries)):
            link = feed.entries[i].link
            if link != last[0]:
                post(name, api, feed.entries[i].title, feed.entries[i].link, db, cursor)
            else:
                break

def main():
    # Read arguments
    argument = argparse.ArgumentParser(
            prog = 'news2tw',
            description = 'Post your feeds on Twitter',
            epilog = 'For lastest version, visit https://github.com/vando/news2tw')
    argument.add_argument('-a', '--add',    dest = 'init', action = 'store_true', help = 'Add a new feed item')
    argument.add_argument('-l', '--list',   dest = 'list', action = 'store_true', help = 'List feeds')
    argument.add_argument('-s', '--status', dest = 'stus', action = 'store_true', help = 'Show status and last feed')
    argument.add_argument('name', nargs='?', help = 'Feed name')
    args = argument.parse_args()
    name = args.name

    # Start DB
    db = sqlite3.connect('feed.sqlite3')
    cursor = db.cursor()
    ifnotexists(db, cursor)

    # INIT
    if args.init:
        if name is None:
            name = raw_input('Feed name: ').strip()
        init(name, db, cursor)
        quit()

    # List
    if args.list:
        list(db, cursor)
        quit()

    # Status
    if args.stus:
        stus(name, db, cursor)
        quit()

    # Download and post
    if args.name:
        cursor.execute('''SELECT inuse FROM feed WHERE name=?''', (name,))
        status = cursor.fetchone()
        if status is None:
            print 'Feed not valid'
            db.close()
            quit(1)
        if status[0] == 'NO':
            cursor.execute('''UPDATE feed SET inuse=? WHERE name=?''', ('YES', name))
            db.commit()
            down(name, db, cursor)
            cursor.execute('''UPDATE feed SET inuse=? WHERE name=?''', ('NO', name))
            db.commit()
            db.close()
    else:
        argument.print_help()
        db.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        quit()
