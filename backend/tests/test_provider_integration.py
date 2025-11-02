import os
import pytest

from app.verify import verify_text


@pytest.mark.integration
def test_verify_provider_smoke():
    """Integration smoke test for external verification provider.

    This test is marked as integration and is deselected by default (see pytest.ini).
    CI will run it only when provider secrets are present.
    """
    # Best-effort: if provider credentials are not configured the call may return a mock value.
    text = "Integration test: The local script requests a verification confidence."
    conf = verify_text(text, timeout=10.0)
    assert isinstance(conf, float) or isinstance(conf, int)
    conf = float(conf)
    assert 0.0 <= conf <= 1.0
