from firstcoder.windows_input_compat import should_drop_key_event


def test_windows_input_filter_keeps_ime_unicode_with_control_state() -> None:
    assert not should_drop_key_event(0x10, 0, "你")


def test_windows_input_filter_drops_control_record_without_unicode() -> None:
    assert should_drop_key_event(0x10, 0, "")


def test_windows_input_filter_keeps_normal_printable_key() -> None:
    assert not should_drop_key_event(0, 65, "a")
