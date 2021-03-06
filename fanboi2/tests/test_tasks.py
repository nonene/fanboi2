import mock
import transaction
import unittest
from fanboi2.models import DBSession
from fanboi2.tests import ModelMixin, TaskMixin


class TestAddTopicTask(TaskMixin, ModelMixin, unittest.TestCase):

    def _makeOne(self, *args, **kwargs):
        from fanboi2.tasks import add_topic
        return add_topic.delay(*args, **kwargs)

    def test_add_topic(self):
        import transaction
        from fanboi2.models import Topic
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            board_id = board.id  # board is not bound outside transaction!
        result = self._makeOne(request, board_id, 'Foobar', 'Hello, world!')
        topic = DBSession.query(Topic).first()
        self.assertTrue(result.successful())
        self.assertEqual(DBSession.query(Topic).count(), 1)
        self.assertEqual(DBSession.query(Topic).get(result.get()[1]), topic)
        self.assertEqual(topic.title, 'Foobar')
        self.assertEqual(topic.posts[0].body, 'Hello, world!')

    @mock.patch('fanboi2.utils.Akismet.spam')
    def test_add_topic_spam(self, akismet):
        from fanboi2.tasks import AddTopicException
        from fanboi2.models import Topic
        akismet.return_value = True
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            board_id = board.id  # board is not bound outside transaction!
        result = self._makeOne(request, board_id, 'Foobar', 'Hello, world!')
        self.assertFalse(result.successful())
        self.assertEqual(DBSession.query(Topic).count(), 0)
        with self.assertRaises(AddTopicException) as e:
            assert not result.get()
        self.assertEqual(e.exception.args, ('spam',))


class TestAddPostTask(TaskMixin, ModelMixin, unittest.TestCase):

    def _makeOne(self, *args, **kwargs):
        from fanboi2.tasks import add_post
        return add_post.delay(*args, **kwargs)

    def test_add_post(self):
        import transaction
        from fanboi2.models import Post
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            topic = self._makeTopic(board=board, title='Hello, world!')
            topic_id = topic.id  # topic is not bound outside transaction!
        result = self._makeOne(request, topic_id, 'Hi!', True)
        post = DBSession.query(Post).first()
        self.assertTrue(result.successful())
        self.assertEqual(DBSession.query(Post).count(), 1)
        self.assertEqual(DBSession.query(Post).get(result.get()[1]), post)
        self.assertEqual(post.body, 'Hi!')
        self.assertEqual(post.bumped, True)

    @mock.patch('fanboi2.utils.Akismet.spam')
    def test_add_post_spam(self, akismet):
        import transaction
        from fanboi2.tasks import AddPostException
        from fanboi2.models import Post
        akismet.return_value = True
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            topic = self._makeTopic(board=board, title='Hello, world!')
            topic_id = topic.id  # topic is not bound outside transaction!
        result = self._makeOne(request, topic_id, 'Hi!', True)
        self.assertFalse(result.successful())
        self.assertEqual(DBSession.query(Post).count(), 0)
        with self.assertRaises(AddPostException) as e:
            assert not result.get()
        self.assertEqual(e.exception.args, ('spam',))

    def test_add_post_locked(self):
        import transaction
        from fanboi2.tasks import AddPostException
        from fanboi2.models import Post
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            topic = self._makeTopic(
                board=board,
                title='Hello, world!',
                status='locked')
            topic_id = topic.id  # topic is not bound outside transaction!
        result = self._makeOne(request, topic_id, 'Hi!', True)
        self.assertFalse(result.successful())
        self.assertEqual(DBSession.query(Post).count(), 0)
        with self.assertRaises(AddPostException) as e:
            assert not result.get()
        self.assertEqual(e.exception.args, ('locked',))

    def test_add_post_retry(self):
        import transaction
        from sqlalchemy.exc import IntegrityError
        request = {'remote_addr': '127.0.0.1'}
        with transaction.manager:
            board = self._makeBoard(title='Foobar', slug='foobar')
            topic = self._makeTopic(board=board, title='Hello, world!')
            topic_id = topic.id  # topic is not bound outside transaction!
        with mock.patch('fanboi2.models.DBSession.flush') as dbs:
            dbs.side_effect = IntegrityError(None, None, None)
            result = self._makeOne(request, topic_id, 'Hi!', True)
        self.assertEqual(dbs.call_count, 5)
        self.assertFalse(result.successful())
