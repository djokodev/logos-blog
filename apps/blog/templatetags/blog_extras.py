import re

import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _autolink_plain_urls(text):
    pattern = re.compile(r"(?<!\]\()https?://[^\s<]+")

    def _replace(match):
        url = match.group(0)
        trailing = ""
        while url and url[-1] in ".,);]":
            trailing = url[-1] + trailing
            url = url[:-1]
        return f"<{url}>{trailing}"

    return pattern.sub(_replace, text)


@register.filter
def markdownify(text):
    if not text:
        return ""
    prepared = _autolink_plain_urls(str(text))
    html = md.markdown(
        prepared,
        extensions=["extra", "sane_lists", "fenced_code", "toc", "nl2br"],
    )
    return mark_safe(html)


@register.filter
def youtube_embed_url(url):
    if not url:
        return ""
    patterns = [
        r"(?:youtube\.com/watch\?v=)([\w-]{11})",
        r"(?:youtube\.com/shorts/)([\w-]{11})",
        r"(?:youtube\.com/live/)([\w-]{11})",
        r"(?:youtu\.be/)([\w-]{11})",
        r"(?:youtube\.com/embed/)([\w-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
    return ""
