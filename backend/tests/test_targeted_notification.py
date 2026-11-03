"""Sending to specific users must not become a way out of your own pool.

The composer gained a recipient picker. The picker is scoped server-side, but
the REQUEST that follows carries bare ids, so the endpoint cannot trust them:
an id pasted by hand, or left over from another admin's session, would
otherwise deliver a notification into somebody else's book of clients.

The other half is the empty selection. "I deselected everyone" and "I did not
use the picker" arrive as `[]` and `None`, and if those collapse, an admin who
clears the list broadcasts to every user they have.

    pytest -q backend/tests/test_targeted_notification.py
"""

from __future__ import annotations

import pytest
from beanie import PydanticObjectId
from fastapi import HTTPException

from app.api.v1.admin.notifications import _narrow_to_picked

MINE = [PydanticObjectId() for _ in range(3)]
THEIRS = PydanticObjectId()


def test_picking_a_subset_sends_to_exactly_that_subset():
    out = _narrow_to_picked([str(MINE[0]), str(MINE[2])], MINE)
    assert out == [MINE[0], MINE[2]]


def test_one_user_is_a_valid_send():
    assert _narrow_to_picked([str(MINE[1])], MINE) == [MINE[1]]


def test_an_id_outside_the_pool_is_dropped():
    out = _narrow_to_picked([str(MINE[0]), str(THEIRS)], MINE)
    assert out == [MINE[0]]


def test_only_outside_ids_is_refused_not_silently_empty():
    """Returning [] here would reach the caller's `if not recipients` and
    report a successful send of zero — an admin would believe it went out."""
    with pytest.raises(HTTPException) as e:
        _narrow_to_picked([str(THEIRS)], MINE)
    assert e.value.status_code == 403


def test_the_refusal_does_not_say_whose_pool_it_is_in():
    """Confirming an id exists elsewhere answers a question the actor is not
    allowed to ask."""
    with pytest.raises(HTTPException) as e:
        _narrow_to_picked([str(THEIRS)], MINE)
    assert str(THEIRS) not in str(e.value.detail)


def test_an_empty_selection_is_an_error_not_everyone():
    """The whole reason `user_ids=None` and `user_ids=[]` stay distinct."""
    with pytest.raises(HTTPException) as e:
        _narrow_to_picked([], MINE)
    assert e.value.status_code == 400


def test_a_malformed_id_is_rejected_rather_than_skipped():
    """Skipping it would quietly send to fewer people than were picked."""
    with pytest.raises(HTTPException) as e:
        _narrow_to_picked([str(MINE[0]), "not-an-id"], MINE)
    assert e.value.status_code == 400


def test_duplicates_do_not_double_send():
    out = _narrow_to_picked([str(MINE[0]), str(MINE[0]), str(MINE[1])], MINE)
    assert out == [MINE[0], MINE[1]]


def test_an_empty_pool_refuses_rather_than_falling_through():
    with pytest.raises(HTTPException) as e:
        _narrow_to_picked([str(MINE[0])], [])
    assert e.value.status_code == 403
