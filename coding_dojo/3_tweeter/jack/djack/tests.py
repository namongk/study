# -*- coding: utf-8 -*-
import json
from unittest import skip

from django.test import TestCase
from django.contrib.auth.models import User

from .models import Tweet, Comment

'''
개별사용자 기능
list
v post (140)
retweet
favorite
follow
'''

# Create your tests here.
class JackTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'password')
        self.client.login(username='test', password='password')

    def test_post_tweet(self):
        response = self.client.post('/jack/create/', {"text": "test tweet"})
        self.assertEqual(response.status_code, 200)
        tweets = Tweet.objects.all()
        self.assertEqual(list(tweets.values_list('text', 'writer__username')),
                         [(u"test tweet", u'test')])
        # self.assertEqual(list(tweets.values_list('writer__username', flat=True)),
                        #[u"test"])

    def test_post_length_limit(self):
        char_141 = 'c' * 141
        response = self.client.post('/jack/create/', {"text": char_141})
        self.assertEqual(response.status_code, 400)
        char_140 = 'c' * 140
        response = self.client.post('/jack/create/', {"text": char_140})
        self.assertEqual(response.status_code, 200)

    def test_list_empty(self):
        response = self.client.get('/jack/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

    def test_list_tweets(self):
        Tweet.objects.create(writer=self.user, text='test tweet 1')
        Tweet.objects.create(writer=self.user, text='test tweet 2')
        response = self.client.get('/jack/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [
            {u'writer': self.user.username, u'text': 'test tweet 1'},
            {u'writer': self.user.username, u'text': 'test tweet 2'},
        ])


class LikeTest(TestCase):
    like_url_fmt = '/jack/like/%d'
    like_list_url_fmt = '/jack/likers/%d'
    detail_url_fmt = '/jack/%d'
    comment_url_fmt = '/jack/%d/comment'

    def setUp(self):
        self.a_user = User.objects.create_user('test1', 'test1@test.com', 'password')
        self.other_user = User.objects.create_user('test2', 'test2@test.com', 'password')

    def _make_tweet(self, user, text='default text'):
        return Tweet.objects.create(writer=user, text=text)
        
    def test_detail_tweet__no_like_initially0(self):
        user1_tweet = self._make_tweet(self.a_user)
        response = self.client.get(self.detail_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 200)
        tweet_dict = json.loads(response.content)
        self.assertEqual(tweet_dict['like'], 0)

    def test_like_count_increased_when_do_like(self):
        user1_tweet = self._make_tweet(self.a_user)
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 401)
        self.client.login(username=self.a_user.username, password='password')
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 200)
        tweet = Tweet.objects.get(id=user1_tweet.id)
        self.assertEqual(tweet.like, 1)
        self.client.login(username=self.other_user.username, password='password')
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 200)
        tweet = Tweet.objects.get(id=user1_tweet.id)
        self.assertEqual(tweet.like, 2)

    def test_prevent_duplicated_like(self):
        user1_tweet = self._make_tweet(self.a_user)
        self.client.login(username=self.a_user.username, password='password')
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 400)
        tweet = Tweet.objects.get(id=user1_tweet.id)
        self.assertEqual(tweet.like, 1)

    def test_like_cancel(self):
        user1_tweet = self._make_tweet(self.a_user)
        self.client.login(username=self.a_user.username, password='password')
        response = self.client.post(self.like_url_fmt % user1_tweet.id)
        self.assertEqual(response.status_code, 200)
        tweet = Tweet.objects.get(id=user1_tweet.id)
        self.assertEqual(tweet.like, 1)
        response = self.client.post(self.like_url_fmt % user1_tweet.id, {'delete': '1'})
        self.assertEqual(response.status_code, 200)
        tweet = Tweet.objects.get(id=user1_tweet.id)
        self.assertEqual(tweet.like, 0)

    def test_remove_all_like_from_deleted_user(self):
        tweet1 = self._make_tweet(self.a_user)
        tweet2 = self._make_tweet(self.a_user)
        tweet3 = self._make_tweet(self.a_user)

        self.client.login(username=self.a_user.username, password='password')
        self.client.post(self.like_url_fmt % tweet1.id)
        self.client.post(self.like_url_fmt % tweet2.id)

        self.client.login(username=self.other_user.username, password='password')
        self.client.post(self.like_url_fmt % tweet2.id)
        self.client.post(self.like_url_fmt % tweet3.id)

        #    T1 T2 T3
        # U1  v  v
        # U2     v  v

        response = self.client.post('/jack/bye/')
        self.assertEqual(response.status_code, 200)
        for tweet in Tweet.objects.filter(id__in=[tweet1.id, tweet2.id]):
            self.assertEqual(tweet.like, 1)
        for tweet in Tweet.objects.filter(id__in=[tweet3.id]):
            self.assertEqual(tweet.like, 0)

        # TODO: likers list up

    def test_likers_list(self):
        tweet1 = self._make_tweet(self.a_user)
        response = self.client.get(self.like_list_url_fmt % tweet1.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

        self.client.login(username=self.a_user.username, password='password')
        self.client.post(self.like_url_fmt % tweet1.id)
        response = self.client.get(self.like_list_url_fmt % tweet1.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [{'username':self.a_user.username,
                                                         'user_id':self.a_user.id}])

        self.client.login(username=self.other_user.username, password='password')
        self.client.post(self.like_url_fmt % tweet1.id)
        response = self.client.get(self.like_list_url_fmt % tweet1.id)
        self.assertEqual(sorted(json.loads(response.content), key=lambda u: u['user_id']), [
            {'username':self.a_user.username,
             'user_id':self.a_user.id},
            {'username':self.other_user.username,
             'user_id':self.other_user.id},
        ])

    # * comment list
    # TODO: tweet-detail - comment list

    def test_comment_to_tweet(self):
        # * comment
        tweet1 = self._make_tweet(self.a_user)
        response = self.client.post(self.comment_url_fmt % tweet1.id, {'text': 'test comment'})
        self.assertEqual(Comment.objects.all().exists(), False)


        self.client.login(username=self.a_user, password='password')
        response = self.client.post(self.comment_url_fmt % tweet1.id, {'text': 'test comment'})
        self.assertEqual(response.status_code, 200)
        comment = tweet1.comment_set.get()
        self.assertEqual(comment.text, 'test comment')
