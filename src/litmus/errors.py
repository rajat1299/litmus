from __future__ import annotations


class LitmusUserError(Exception):
    """Expected Litmus-facing failure that should surface without a traceback."""


class AppDiscoveryError(LitmusUserError, LookupError):
    """Litmus could not discover the target ASGI app."""


class VerificationScopeError(LitmusUserError, ValueError):
    """The requested verification scope could not be resolved."""


class ReplayLookupError(LitmusUserError, LookupError):
    """A requested replay trace could not be found in the run store."""

