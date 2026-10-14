import pytest
from main import app

@pytest.fixture(autouse=True)
def disable_rate_limiting():
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False
    yield
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = True
