from site_test.fetcher import build_launch_options

def test_launch_options_no_proxy():
    assert build_launch_options(None) == {"headless": True}

def test_launch_options_with_proxy():
    opts = build_launch_options("http://x:8000")
    assert opts["proxy"] == {"server": "http://x:8000"}
    assert opts["headless"] is True
