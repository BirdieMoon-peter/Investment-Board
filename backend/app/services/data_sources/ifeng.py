"""Ifeng news parser exists but is not in the default managed sync chain."""
from .contracts import SourceModule, endpoint, field


def get_module():
    return SourceModule('ifeng', 'Ifeng', (
        endpoint('ifeng', 'news', 'https://finance.ifeng.com/app/hq/stock/{market}{stock_code}/news', (
            field('article.news-item a text', 'title', conversion='join stripped text', missing='reject missing rows/title'),
            field('time datetime|text', 'published_at', 'ISO datetime', 'UTC datetime', 'naive assigned UTC; aware converted UTC', missing='reject absent', verification='unverified'),
            field('a href', 'url', conversion='urljoin Ifeng origin'),
            field('p text', 'summary', conversion='join stripped text'),
        ), payload='HTML', time='Naive source timezone unverified; parser assigns UTC.', scope='planned', limitations=('Existing parser only; not wired into default stock sync or homepage. Planned integration does not mean parser missing.',)),
    ))


def build_news_adapter(constructor=None):
    from app.services.providers import RawNewsSourceAdapter
    from app.services.providers.ifeng_news import IfengNewsSource
    return RawNewsSourceAdapter('ifeng', (constructor or IfengNewsSource)())
