import unittest
from fanboi2.tests import ModelMixin
from pyramid import testing


class TestFormatters(unittest.TestCase):

    def _makeRegistry(self):
        from pyramid.registry import Registry
        registry = Registry()
        registry.settings = {'app.timezone': 'Asia/Bangkok'}
        return registry

    def test_url_fix(self):
        from fanboi2.formatters import url_fix
        tests = [
            ('http://example.com/',
             'http://example.com/'),
            ('https://example.com:443/foo/bar',
             'https://example.com:443/foo/bar'),
            ('http://example.com/lots of space',
             'http://example.com/lots%20of%20space'),
            ('http://example.com/search?q=hello world',
             'http://example.com/search?q=hello+world'),
            ('http://example.com/ほげ',
             'http://example.com/%E3%81%BB%E3%81%92'),
            ('http://example.com/"><script></script>',
             'http://example.com/%22%3E%3Cscript%3E%3C/script%3E'),
        ]
        for source, target in tests:
            self.assertEqual(url_fix(source), target)

    def test_extract_thumbnail(self):
        from fanboi2.formatters import extract_thumbnail
        text = """
        Inline page: http://imgur.com/image1
        Inline image: http://i.imgur.com/image2.jpg
        Subdomain image: http://fanboi2.imgur.com/image3.png

        http://i.imgur.com/image4.jpeg
        http://i.imgur.com/image5.gif
        http://imgur.com/<script>alert("haxx0red!!")</script>.jpg
        http://<script></script>.imgur.com/image6.gif
        http://imgur.com/ほげ

        Lorem ipsum dolor sit amet.

        https://imgur.com/image5
        https://i.imgur.com/image7.jpg
        """
        self.assertTupleEqual(tuple(extract_thumbnail(text)), (
            ('//i.imgur.com/image1s.jpg', '//imgur.com/image1'),
            ('//i.imgur.com/image2s.jpg', '//imgur.com/image2'),
            ('//i.imgur.com/image3s.jpg', '//imgur.com/image3'),
            ('//i.imgur.com/image4s.jpg', '//imgur.com/image4'),
            ('//i.imgur.com/image5s.jpg', '//imgur.com/image5'),
            ('//i.imgur.com/image7s.jpg', '//imgur.com/image7'),
        ))

    def test_post_markup(self):
        from fanboi2.formatters import PostMarkup
        from jinja2 import Markup
        markup = PostMarkup('<p>foo</p>')
        markup.shortened = True
        markup.length = 3
        self.assertEqual(markup, Markup('<p>foo</p>'))
        self.assertEqual(markup.shortened, True)
        self.assertEqual(len(PostMarkup('<p>Hello</p>')), 12)
        self.assertEqual(len(markup), 3)

    def test_format_text(self):
        from fanboi2.formatters import format_text
        from jinja2 import Markup
        tests = [
            ('Hello, world!', '<p>Hello, world!</p>'),
            ('H\n\n\nello\nworld', '<p>H</p>\n<p>ello<br>world</p>'),
            ('Foo\r\n\r\n\r\n\nBar', '<p>Foo</p>\n<p>Bar</p>'),
            ('Newline at the end\n', '<p>Newline at the end</p>'),
            ('STRIP ME!!!1\n\n', '<p>STRIP ME!!!1</p>'),
            ('ほげ\n\nほげ', '<p>ほげ</p>\n<p>ほげ</p>'),
            ('Foo\n \n Bar', '<p>Foo</p>\n<p>Bar</p>'),
            ('ไก่จิกเด็ก\n\nตายบนปากโอ่ง',
             '<p>ไก่จิกเด็ก</p>\n<p>ตายบนปากโอ่ง</p>'),
            ('<script></script>', '<p>&lt;script&gt;&lt;/script&gt;</p>'),
        ]
        for source, target in tests:
            self.assertEqual(format_text(source), Markup(target))

    def test_format_text_autolink(self):
        from fanboi2.formatters import format_text
        from jinja2 import Markup
        text = ('Hello from autolink:\n\n'
                'Boom: http://example.com/"<script>alert("Hi")</script><a\n'
                'http://www.example.com/ほげ\n'
                'http://www.example.com/%E3%81%BB%E3%81%92\n'
                'https://www.example.com/test foobar')
        self.assertEqual(
            format_text(text),
            Markup('<p>Hello from autolink:</p>\n'
                   '<p>Boom: <a href="http://example.com/%22%3Cscript'
                   '%3Ealert%28%22Hi%22%29%3C/script%3E%3Ca" '
                   'class="link" target="_blank" rel="nofollow">'
                   'http://example.com/&quot;&lt;script&gt;alert(&quot;'
                   'Hi&quot;)&lt;/script&gt;&lt;a</a><br>'
                   '<a href="http://www.example.com/%E3%81%BB%E3%81%92" '
                   'class="link" target="_blank" rel="nofollow">'
                   'http://www.example.com/ほげ</a><br>'
                   '<a href="http://www.example.com/%E3%81%BB%E3%81%92" '
                   'class="link" target="_blank" rel="nofollow">'
                   'http://www.example.com/ほげ</a><br>'
                   '<a href="https://www.example.com/test" '
                   'class="link" target="_blank" rel="nofollow">'
                   'https://www.example.com/test</a> foobar</p>'))

    def test_format_text_shorten(self):
        from fanboi2.formatters import format_text
        from fanboi2.formatters import PostMarkup
        from jinja2 import Markup
        tests = (
            ('Hello, world!', '<p>Hello, world!</p>', 13, False),
            ('Hello\nworld!', '<p>Hello</p>', 5, True),
            ('Hello, world!\nFoobar', '<p>Hello, world!</p>', 13, True),
            ('Hello', '<p>Hello</p>', 5, False),
        )
        for source, target, length, shortened in tests:
            result = format_text(source, shorten=5)
            self.assertIsInstance(result, PostMarkup)
            self.assertEqual(result, Markup(target))
            self.assertEqual(result.length, length)
            self.assertEqual(result.shortened, shortened)

    def test_format_text_thumbnail(self):
        from fanboi2.formatters import format_text
        from jinja2 import Markup
        text = ("New product! https://imgur.com/foobar1\n\n"
                "http://i.imgur.com/foobar2.png\n"
                "http://imgur.com/foobar3.jpg\n"
                "Buy today get TWO for FREE!!1")
        self.assertEqual(
            format_text(text),
            Markup('<p>New product! <a href="https://imgur.com/foobar1" '
                   'class="link" target="_blank" rel="nofollow">'
                   'https://imgur.com/foobar1</a></p>\n'
                   '<p><a href="http://i.imgur.com/foobar2.png" '
                   'class="link" target="_blank" rel="nofollow">'
                   'http://i.imgur.com/foobar2.png</a><br>'
                   '<a href="http://imgur.com/foobar3.jpg" class="link" '
                   'target="_blank" rel="nofollow">'
                   'http://imgur.com/foobar3.jpg</a><br>'
                   'Buy today get TWO for FREE!!1</p>\n'
                   '<p class="thumbnails"><a href="//imgur.com/foobar1" '
                   'class="thumbnail" target="_blank">'
                   '<img src="//i.imgur.com/foobar1s.jpg">'
                   '</a>'
                   '<a href="//imgur.com/foobar2" '
                   'class="thumbnail" target="_blank">'
                   '<img src="//i.imgur.com/foobar2s.jpg">'
                   '</a>'
                   '<a href="//imgur.com/foobar3" '
                   'class="thumbnail" target="_blank">'
                   '<img src="//i.imgur.com/foobar3s.jpg">'
                   '</a>'
                   '</p>'))

    def test_format_markdown(self):
        from fanboi2.formatters import format_markdown
        from jinja2 import Markup
        tests = [
            ('**Hello, world!**', '<p><strong>Hello, world!</strong></p>\n'),
            ('<b>Foobar</b>', '<p><b>Foobar</b></p>\n'),
            ('Split\n\nParagraph', '<p>Split</p>\n\n<p>Paragraph</p>\n'),
            ('Split\nlines', '<p>Split\nlines</p>\n'),
        ]
        for source, target in tests:
            self.assertEqual(format_markdown(source), Markup(target))

    def test_format_markdown_empty(self):
        from fanboi2.formatters import format_markdown
        self.assertIsNone(format_markdown(None))

    def test_format_datetime(self):
        from datetime import datetime, timezone
        from fanboi2.formatters import format_datetime
        testing.setUp(registry=self._makeRegistry())
        d1 = datetime(2013, 1, 2, 0, 4, 1, 0, timezone.utc)
        d2 = datetime(2012, 12, 31, 16, 59, 59, 0, timezone.utc)
        self.assertEqual(format_datetime(d1), "Jan 02, 2013 at 07:04:01")
        self.assertEqual(format_datetime(d2), "Dec 31, 2012 at 23:59:59")

    def test_format_isotime(self):
        from datetime import datetime, timezone, timedelta
        from fanboi2.formatters import format_isotime
        ict = timezone(timedelta(hours=7))
        testing.setUp(registry=self._makeRegistry())
        d1 = datetime(2013, 1, 2, 7, 4, 1, 0, ict)
        d2 = datetime(2012, 12, 31, 23, 59, 59, 0, ict)
        self.assertEqual(format_isotime(d1), "2013-01-02T00:04:01Z")
        self.assertEqual(format_isotime(d2), "2012-12-31T16:59:59Z")


class TestFormattersWithModel(ModelMixin, unittest.TestCase):

    def test_format_post(self):
        from fanboi2.formatters import format_post
        from jinja2 import Markup
        self.config.add_route('topic_scoped', '/{board}/{topic}/{query}')
        board = self._makeBoard(title="Foobar", slug="foobar")
        topic = self._makeTopic(board=board, title="Hogehogehogehogehoge")
        post1 = self._makePost(topic=topic, body="Hogehoge\nHogehoge")
        post2 = self._makePost(topic=topic, body=">>1")
        post3 = self._makePost(topic=topic, body=">>1-2\nHoge")
        tests = [
            (post1, "<p>Hogehoge<br>Hogehoge</p>"),
            (post2, "<p><a data-number=\"1\" " +
                    "href=\"/foobar/1/1\" class=\"anchor\">" +
                    "&gt;&gt;1</a></p>"),
            (post3, "<p><a data-number=\"1-2\" " +
                    "href=\"/foobar/1/1-2\" class=\"anchor\">" +
                    "&gt;&gt;1-2</a><br>Hoge</p>"),
        ]
        for source, target in tests:
            self.assertEqual(format_post(source), Markup(target))

    def test_format_post_shorten(self):
        from fanboi2.formatters import format_post
        from jinja2 import Markup
        self.config.add_route('topic_scoped', '/{board}/{topic}/{query}')
        board = self._makeBoard(title="Foobar", slug="foobar")
        topic = self._makeTopic(board=board, title="Hogehogehogehogehoge")
        post = self._makePost(topic=topic, body="Hello\nworld")
        self.assertEqual(format_post(post, shorten=5),
                         Markup("<p>Hello</p>\n<p class=\"shortened\">"
                                "Post shortened. <a href=\"/foobar/1/1-\">"
                                "See full post</a>.</p>"))
