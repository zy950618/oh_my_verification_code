from __future__ import annotations

import pytest

from adapter import {{ class_name }}Adapter


def test_generated_adapter_fails_closed() -> None:
    adapter = {{ class_name }}Adapter()
    with pytest.raises(NotImplementedError):
        adapter.classify(object())
    with pytest.raises(NotImplementedError):
        adapter.solve(object())


def test_generated_adapter_declares_stable_id() -> None:
    assert {{ class_name }}Adapter.adapter_id == "{{ adapter_id }}"
