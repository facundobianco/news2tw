# news2tw v0.7

### Description

news2tw (*News to Twitter*) is a Python script to deliver news' feed to Twitter. It's similar to other scripts you can found on the Internet but I created for breaking news.

TODO: Create a post in medium to explain it.

### Features

* Use Sqlite3 database for storing data.
* Shrink message length without trimming the last word.
* TODO: Reddit: Use the link insted of the URL to subreddit post.

### How to use

#### Add a new feed

First, [create your Twitter application](https://apps.twitter.com/app/new) and generate the keys: *Consumer key* and *Consumer secret*. Do not forget to enable read and write access in the *Permissions* tab.

Then, run

```
news2py -a <your_feed_alias>
```

#### List feeds 

```
news2py -l
```

### Twitter accounts powered by news2tw 

They are unofficial accounts.

[![Liveuamap Middle East](imgs/1516466132.png)](https://twitter.com/lummideastrss2)
