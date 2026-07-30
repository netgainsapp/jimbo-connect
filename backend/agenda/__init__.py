"""Agenda Builder: a free, standalone tool that turns event details plus a list
of sessions into a polished Word document.

Phase 1 is deliberately stateless. Nothing here touches Mongo: the client holds
the draft in localStorage and POSTs the whole agenda to /api/agenda/export,
which validates it and streams back a .docx. That keeps anonymous use free of
database rows entirely, so there is nothing to orphan or clean up.

See docs/AGENDA-BUILDER-PROPOSAL.md for the full design and the decisions
behind it.
"""
