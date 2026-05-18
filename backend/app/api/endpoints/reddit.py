"""
Reddit endpoints deprecated.

This module is deprecated as of the removal of static Reddit sources.
Users can still add Reddit subreddits as dynamic sources via the /monitoring/sources API
using the generic source type system. All collected Reddit items are stored in the
generic `collected_items` collection and can be queried through /monitoring/items endpoints.
"""


# This module is deprecated. Reddit subreddits can be added as dynamic sources
# via the /monitoring/sources API endpoint.
