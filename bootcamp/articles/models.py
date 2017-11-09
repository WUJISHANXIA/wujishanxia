#! -*- coding:utf-8 -*-

from __future__ import unicode_literals

import sys
from django.contrib.auth.models import User
from django.db import models
from autoslug import AutoSlugField
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count

import markdown
from taggit.managers import TaggableManager

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3:
    from html.parser import HTMLParser
else:
    from HTMLParser import HTMLParser


@python_2_unicode_compatible
class Article(models.Model):
    DRAFT = 'D'
    PUBLISHED = 'P'
    STATUS = (
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
    )

    title = models.CharField(max_length=255, null=False, unique=True)
    slug = AutoSlugField(populate_from='title')
    tags = TaggableManager()
    content = models.TextField(max_length=4000)
    status = models.CharField(max_length=1, choices=STATUS, default=DRAFT)
    create_user = models.ForeignKey(User)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    update_user = models.ForeignKey(User, null=True, blank=True,
                                    related_name="+")

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ("-create_date",)

    def __str__(self):
        return self.title

    def get_content_as_markdown(self):
        return markdown.markdown(self.content, safe_mode='escape')

    @staticmethod
    def get_published():
        articles = Article.objects.filter(status=Article.PUBLISHED)
        return articles

    @staticmethod
    def get_counted_tags():
        tag_dict = {}
        query = Article.objects.filter(status='P').annotate(tagged=Count(
            'tags')).filter(tags__gt=0)
        for obj in query:
            for tag in obj.tags.names():
                if tag not in tag_dict:
                    tag_dict[tag] = 1

                else:  # pragma: no cover
                    tag_dict[tag] += 1

        return tag_dict.items()

    def get_summary(self):
        if len(self.content) > 255:
            # return '{0}...'.format(self.content[:255])
            return '{0}'.format(self.content[:255])
        else:
            return self.content

    def get_summary_as_markdown(self):
        markdown_html = markdown.markdown(self.get_summary(), safe_mode='escape')
        summary_parser = SummaryParser()
        summary_parser.feed(markdown_html)
        summary = self.insert_space_to_long_word(summary_parser.summary)
        return summary.replace('[TOC]', '', 1).replace('目录', '', 1)

    def get_comments(self):
        return ArticleComment.objects.filter(article=self)

    @staticmethod
    def insert_space_to_long_word(content):
        count = 0
        index_list = []
        for index, character in enumerate(content):
            if not character.isspace():
                count += 1
            else:
                count = 0
            if count >= 50:
                index_list.append(index)
                count = 0
        content_list = list(content)
        for index in index_list:
            content_list.insert(index, ' ')
        content = ''.join(content_list)
        return content


@python_2_unicode_compatible
class ArticleComment(models.Model):
    article = models.ForeignKey(Article)
    comment = models.CharField(max_length=500)
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = _("Article Comment")
        verbose_name_plural = _("Article Comments")
        ordering = ("date",)

    def __str__(self):
        return '{0} - {1}'.format(self.user.username, self.article.title)

    def get_comment_as_markdown(self):
        return markdown.markdown(self.comment, safe_mode='escape')


class SummaryParser(HTMLParser):
    """Get a summary of the HTML-format document"""

    def __init__(self):
       HTMLParser.__init__(self)
       self.summary = ''

    def handle_data(self, data):
        if self.summary:
            self.summary = ' '.join([self.summary, data])
        else:
            self.summary = data

