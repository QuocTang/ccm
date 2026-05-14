from ccm.paths import fmt_size, naive_decode


def test_naive_decode_strips_leading_dash():
    assert naive_decode("-home-quoctang-foo") == "/home/quoctang/foo"


def test_naive_decode_passthrough_without_leading_dash():
    assert naive_decode("plain") == "plain"


def test_fmt_size_bytes():
    assert fmt_size(512) == "512B"


def test_fmt_size_kilobytes():
    out = fmt_size(2 * 1024)
    assert out.endswith("K") and out.startswith("2")


def test_fmt_size_megabytes():
    out = fmt_size(5 * 1024 * 1024)
    assert out.endswith("M")
