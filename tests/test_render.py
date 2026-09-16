from typing import Any

import pytest

from gl_team_cli.render import _target_prefix


class FakeEvent:
    """Stand-in pour un RESTObject : `_target_prefix` ne lit que des attributs."""

    def __init__(self, **attrs: Any) -> None:
        self.__dict__.update(attrs)


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (FakeEvent(target_type="Issue", target_iid=40), "[bold orange3]#40[/bold orange3] "),
        (
            FakeEvent(target_type="MergeRequest", target_iid=17),
            "[bold medium_purple]!17[/bold medium_purple] ",
        ),
        (
            FakeEvent(target_type="Note", note={"noteable_type": "Issue", "noteable_iid": 12}),
            "[bold orange3]#12[/bold orange3] ",
        ),
        (
            FakeEvent(
                target_type="DiffNote",
                note={"noteable_type": "MergeRequest", "noteable_iid": 5},
            ),
            "[bold medium_purple]!5[/bold medium_purple] ",
        ),
        # Cas sans reference : rien a prefixer.
        (FakeEvent(target_type="Milestone", target_iid=3), ""),
        (FakeEvent(target_type="Issue", target_iid=None), ""),
        (FakeEvent(target_type=None), ""),
        (FakeEvent(target_type="Note", note=None), ""),
    ],
)
def test_target_prefix(event: FakeEvent, expected: str) -> None:
    assert _target_prefix(event) == expected  # type: ignore[arg-type]
