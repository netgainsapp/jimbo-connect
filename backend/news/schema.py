"""Input + storage schema for the news section.

Unlike the blog (AI-generated, guardrail-checked), news items are authored by an
admin: the person supplies the headline, summary, prose sections, and at least
one real source URL. Nothing here fabricates events or sources; the source_url
is required and must be http/https so every published item is attributable.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from blog.schema import Section, slugify  # reuse the shared section + slug


def _require_http(v: str) -> str:
    if not isinstance(v, str) or not (v.startswith("http://") or v.startswith("https://")):
        raise ValueError("source must be an http or https URL")
    return v


class NewsArticleInput(BaseModel):
    """What an admin submits to create a news item."""

    headline: str = Field(min_length=8, max_length=140, description="Headline, no dashes")
    summary: str = Field(min_length=8, max_length=400)
    sections: List[Section] = Field(min_length=1)
    source_url: str = Field(description="Primary source URL (required, http/https)")
    sources: List[str] = Field(default_factory=list, description="Additional source URLs")
    event_date: Optional[str] = Field(
        default=None, max_length=40, description="When the event happened (display string)"
    )
    image_url: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("source_url")
    @classmethod
    def _primary_is_http(cls, v):
        return _require_http(v)

    @field_validator("sources")
    @classmethod
    def _extras_are_http(cls, v):
        return [_require_http(u) for u in (v or [])]

    @field_validator("image_url")
    @classmethod
    def _image_https(cls, v):
        if v and not v.startswith("https://"):
            raise ValueError("image_url must be https")
        return v


class GeneratedNews(BaseModel):
    """What the model must return when writing up a source article.

    Note what is absent: there is no URL field. The model is never asked for a
    source, because a source it produced would be a source it could invent. The
    pipeline supplies `source_url` from the feed item it actually fetched, and
    `news.guardrails` rejects anything whose source is not one of those.
    """

    headline: str = Field(description="Headline, 20 to 140 characters, no dashes")
    summary: str = Field(description="One or two sentence summary, no dashes")
    sections: List[Section] = Field(description="At least two sections")
    event_date: Optional[str] = Field(
        default=None,
        description="When this happened, as a short display string, if the source says",
    )


def article_slug(headline: str) -> str:
    return slugify(headline)
