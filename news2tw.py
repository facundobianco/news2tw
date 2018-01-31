#!/usr/bin/env python
#
# maintainer @vando
# https://github.com/vando/rss2tw

import argparse
import feedparser
import logging
import os
import re
import tweepy
import yaml

def rdir(ddir):
    """
    Create configuration directory and/or
    return directory expanded
    """
    if not os.path.exists(ddir):
        os.makedirs(ddir, 0700)
        logging.debug('  Created %s (mode 0700)', ddir)
    if os.stat(ddir).st_mode > 16832:
        print os.stat(ddir)
        logging.debug('  Correct %s permissions to 0700', ddir)
    logging.debug('  Data directory is %s', ddir)
    return ddir

def rcfg(dnam):
    """
    Return the configuration YAML
    """
    conf = dnam + '/config.yml'
    if not os.path.exists(conf):
        os.mknod(conf)
        logging.debug('  Created empty configuration file')
    logging.debug('  Configuration file is %s', conf)
    return conf

def rdat(conf, name):
    """
    Return valid YAML data
    """
    with open(conf, 'r') as stream:
        data = yaml.safe_load(stream)
    try:
        vals = data[name]
    except KeyError:
        print('Feed item %s doesn\'t exist. Quit.' % name)
        return False
    else:
        return vals

def list(conf):
    """
    List feed and related info
    (for searching, use `grep -A3 <value>`)
    """
    with open(conf, 'r') as stream:
        data = yaml.safe_load(stream)
    for i in data:
        print('[%s]' % i)
        print('Twitter: %s' % data[i]['user'])
        print('RSS: %s' % data[i]['url'])
        print('Last tweet: %s' % data[i]['last'])
        print('')

def tkns():
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
        quit(1)
    pin = raw_input('Verification pin number from twitter.com: ').strip()
    try:
        auth.get_access_token(verifier=pin)
    except tweepy.TweepError:
        print 'Error: Failed to get access token.'
        quit(1)
    auth.set_access_token(auth.access_token, auth.access_token_secret)
    api = tweepy.API(auth)
    user = api.me()
    logging.debug('  Requested keys: OK')
    return user.screen_name, url, consumer_key, consumer_secret, auth.access_token, auth.access_token_secret

def newf(conf, name, keys):
    """
    Save new feed configuration and its keys
    keys = screen_name, feed's url, consumer_key, consumer_secret, token_key, token_secret
    """
    data = {name:{'user':keys[0], 'url':keys[1], 'consumer_key':keys[2], 'consumer_secret':keys[3], 'token_key':keys[4], 'token_secret':keys[5], 'last':None, 'etag':None}}
    with open(conf, 'a') as stream:
        yaml.safe_dump(data, stream, default_flow_style=False)
    logging.debug('  Saved data for', name)

def ppid(dnam, dlte):
    """
    Manage news2tw's flow
    ppid(ddir, <True|False>)
    """
    pidn = dnam + '/news2tw.pid'
    logging.debug('  PID file is %s', pidn)
    logging.debug('  PID file delete: %s', dlte)
    pidf = os.path.exists(pidn)
    if not dlte:
        if not pidf:
            gpid = str(os.getpid())
            with open(pidn, 'w') as pid_file:
                pid_file.write(gpid + '\n')
            logging.debug('  PID file has ID %s', gpid)
            return True
        else:
            logging.debug('  PID file %s exists', pidn)
            return False
    else:
        os.remove(pidn)
        logging.debug('  Removed PID file %s. Quit.', pidn)
        quit()

def clan(conf, name):
    """
    Clean up all feeds' last link
    if feed name isn't provided
    """
    with open(conf, 'r') as stream:
        data = yaml.safe_load(stream)
    if name:
        data[name]['last'] = None
    else:
        ansr = ""
        while ansr not in ['y', 'n']:
            ansr = raw_input('Are you sure to clean up all feeds? [y/N] ').lower() or 'n'
        if ansr == 'y':
            for i in data:
                logging.debug('  Cleaning last feed for %s', i)
                data[i]['last'] = None
    with open(conf, 'w') as stream:
        yaml.safe_dump(data, stream, default_flow_style=False)

def auth(data):
    """
    Authenticate with stored tokens
    """
    auth = tweepy.OAuthHandler(data['consumer_key'], data['consumer_secret'])
    auth.set_access_token(data['token_key'], data['token_secret'])
    logging.debug('  Loaded authorization keys')
    api = tweepy.API(auth)
    logging.debug('  Authentication: OK')
    return api

def down(url):
    """
    Get feeds
    """
    logging.debug('  Downloading feed for %s', url)
    feed = feedparser.parse(url)
    if feed.status != 200 or not feed.entries:
        logging.debug('  Feed status: %s', feed.status)
        logging.debug('  Feed entries: %s', feed.entries)
        print('Cannot download feed. Quit.')
        return False
    else:
        logging.debug('  Feed downloaded')
        return feed

def clnk(link, desc):
    """
    Clean Reddit URL to news or
    return the link
    """
    if link.find('reddit.com') > -1:
        start = '^.*<br /> <span><a href="'
        end = '">\[link\].*$'
        link = re.search('%s(.*)%s' % (start, end), desc).group(1)
    logging.debug('  Feed link is %s', link)
    return link

def post(api, title, link, name):
    """
    (If required) Trim tweet and/or
    post it
    """
    if len(title) > 257:
        tweet = re.sub(' [^ ]*$', '...', title[0:250]) + ' ' + link
        logging.debug('  Trimmed tweet.')
    else:
        tweet = title + ' ' + link
    try:
        logging.debug('  Tweet will be: %s', tweet)
        api.update_status(status=tweet)
    except tweepy.TweepError as e:
        logging.debug('  Cannot post tweet %s.' % link)
        logging.debug('  ERR %d: %s. Quit.', e.args[0][0]['code'], e.args[0][0]['message'])
        if e.args[0][0]['code'] != 187:
            raise
        else:
            logging.debug('  Continue.')
            pass
    else:
        pass

def save(conf, link, name):
    """
    Save the last post
    """
    with open(conf, 'r') as stream:
        data = yaml.safe_load(stream)
    data[name]['last'] = link
    with open(conf, 'w') as stream:
        yaml.safe_dump(data, stream, default_flow_style=False)
    logging.debug('  Updated last tweet in YAML.')

def main():
    """
    core
    """
    # Read arguments
    argument = argparse.ArgumentParser(
            prog = 'news2tw',
            description = 'Post your feeds on Twitter',
            epilog = 'For lastest version, visit https://github.com/vando/news2tw')
    argument.add_argument('-d', '--dest-dir', dest = 'ddir', default = '~/.news2tw', help = 'Data directory (default: ${HOME}/.news2tw)')
    argument.add_argument('-a', '--add',      dest = 'init', action = 'store_true',  help = 'Add a new feed item')
    argument.add_argument('-l', '--list',     dest = 'list', action = 'store_true',  help = 'List feeds')
    argument.add_argument('-p', '--print',    dest = 'prnt', action = 'store_true',  help = 'Print feed\'s last 10 items')
    argument.add_argument('-c', '-clean',     dest = 'clan', action = 'store_true',  help = 'Clean last tweet for feed')
    argument.add_argument('--clean-all',      dest = 'call', action = 'store_true',  help = 'Clean last tweet for all feeds')
    argument.add_argument('-v', '--verbose',  dest = 'verb', action = 'store_true',  help = 'Verbose (debug) logging')
    argument.add_argument('name', nargs='?', help = 'Feed name')
    args = argument.parse_args()
    name = args.name
    ddir = args.ddir
    # Logging options (set DEBUG)
    if args.verb:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
    # Data directory
    dnam = rdir(os.path.expanduser(ddir))
    conf = rcfg(dnam)
    size = os.stat(conf).st_size
    logging.debug('  Configuration file size: %d', size)
    #
    # main options
    # ------------
    #
    # Run INIT if config file is empty
    # or get the INIT option
    if size == 0 or args.init:
        if size == 0:
            print('Add your first feed!')
        if name is None:
            name = raw_input('Feed name: ').strip()
        else:
            print('Feed name is %s' % name)
        keys = tkns()
        newf(conf, name, keys)
        quit(0)
    #
    # List feeds and status
    if args.list and size > 0:
        list(conf)
        quit(0)
    if args.list and size == 0:
        print('Configuration file is empty. Quit.')
        quit(1)
    # 
    # Print feed's last 10 items
    if args.prnt and size > 0:
        if name:
            data = rdat(conf, name)
            feed = down(data['url'])
            for i in range(0,10,1):
                link = clnk(feed.entries[i].link, feed.entries[i].description)
                print('Title: %s' % feed.entries[i].title)
                print('URL: %s' % link)
                print('')
            quit(0)
        else:
            print('Not feed name provided. Quit.')
            quit(1)
    if args.list and size == 0:
        print('Configuration file is empty. Quit.')
        quit(1)
    # No option provided and
    # configuration files > 0
    if not name and not args.clan and not args.call:
        logging.debug('  Not argument provided. Show help.')
        argument.print_help()
        quit()
    #
    # PID control
    # (Required for the next functions)
    flow = ppid(dnam, False)
    # 
    # Clean one feed
    # or all feeds
    if args.clan or args.call:
        if args.clan and not name:
            print('Feed name is required. Quit.')
            ppid(dnam, True)
            quit(1)
        if size > 0:
            if flow:
                clan(conf, name)
                ppid(dnam, True)
                quit(0)
            else:
                print('Wait for the next time. Quit.')
                quit(0)
        else:
            print('Configuration file is empty. Quit.')
            ppid(dnam, True)
            quit(1)
    # 
    # Get new entries and tweet it
    if name and flow:
        data = rdat(conf, name)
        if not data:
            ppid(dnam, True)
        api = auth(data)
        last = data['last']
        logging.debug('  Last tweet was: %s', last)
        feed = down(data['url'])
        if not feed:
            ppid(dnam, True)
    # Do the magic
        if last is None:
            logging.debug('  Last tweet is None')
            link = clnk(feed.entries[0].link, feed.entries[0].description)
            try:
                post(api, feed.entries[0].title, link, name)
            except:
                ppid(dnam, True)
                quit(1)
            else:
                save(conf, link, name)
        else:
            logging.debug('  Last tweet isn\'t None.')
            j = -1
            for i in range(len(feed.entries)):
                link = clnk(feed.entries[i].link, feed.entries[i].description)
                if link == last:
                    logging.debug('  Last link and latest tweet are the same.')
                    break
                else:
                    j += 1
            if j > -1:
                logging.debug('  Post the latest news.')
                logging.debug('  Newest news are: %d', j)
                for i in range(j,-1,-1):
                    logging.debug('  (From oldest to newest) News numer #%d', i)
                    link = clnk(feed.entries[i].link, feed.entries[i].description)
                    try:
                        post(api, feed.entries[i].title, link, name)
                    except:
                        ppid(dnam, True)
                        quit(1)
                    else:
                        save(conf, link, name)
        ppid(dnam, True)
    # If the application running?
    if name and not flow:
        logging.debug('  Wait for next time. Quit.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        quit()
