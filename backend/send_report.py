"""One shape for reporting why sends failed, shared by every bulk send path.

A summary is per reason and never per recipient: a host needs to know that
thirty messages died on one cause, not which thirty addresses they were. That
also keeps the response small on a big send, and keeps guest addresses out of
a payload that exists to describe an error.

The reason text is not a closed set, because Resend echoes fragments of the
request back in some errors. So both the key length and the number of distinct
keys are capped, and anything past the cap collapses into "other" rather than
letting the summary grow with the size of the send.
"""

MAX_FAILURE_KINDS = 5
MAX_REASON_LEN = 120


def tally_failure(failures: dict, reason) -> None:
    """Count one failure under a normalised reason. Mutates `failures`."""
    key = " ".join(str(reason or "").split())[:MAX_REASON_LEN] or "unknown"
    if key not in failures and len(failures) >= MAX_FAILURE_KINDS:
        key = "other"
    failures[key] = failures.get(key, 0) + 1
