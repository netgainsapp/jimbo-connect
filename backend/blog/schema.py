"""Structured-output and storage schemas for the blog engine.

The model returns a GeneratedPost (prose only). It never writes numbers, dashes,
markdown, or URLs; the guardrails enforce that after generation. Any numeric
"data" in a post is rendered separately from DB values, never from the model.
"""
import re
from typing import List, Optional

from pydantic import BaseModel, Field


class Section(BaseModel):
    heading: str = Field(description="Short section heading, no dashes")
    body: str = Field(description="One or more sentences of prose, no numbers, no dashes, no markdown")


class GeneratedPost(BaseModel):
    """What the model must return. Validated by guardrails before it can publish."""

    title: str = Field(description="Headline, roughly 20 to 70 characters, no dashes")
    summary: str = Field(description="A one or two sentence summary, no dashes")
    sections: List[Section] = Field(description="At least three sections")
    cta: str = Field(description="A closing line inviting the reader to use Intro Connect")


def slugify(title: str) -> str:
    """URL slug from a title: lowercase, words joined by single hyphens."""
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def post_text(post: GeneratedPost) -> str:
    """All human-visible generated text, for guardrail scanning and similarity."""
    parts = [post.title, post.summary]
    for s in post.sections:
        parts.append(s.heading)
        parts.append(s.body)
    parts.append(post.cta)
    return "\n".join(p for p in parts if p)


def doc_text(doc: dict) -> str:
    """Same concatenation for a stored post doc (for dedupe/similarity checks)."""
    parts = [doc.get("title", ""), doc.get("summary", "")]
    for s in doc.get("sections", []) or []:
        parts.append(s.get("heading", ""))
        parts.append(s.get("body", ""))
    parts.append(doc.get("cta", ""))
    return "\n".join(p for p in parts if p)
