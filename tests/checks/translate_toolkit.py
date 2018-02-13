import pytest
from mock import MagicMock

from pontoon.checks.utils.translate_toolkit import quality_check


@pytest.yield_fixture()
def mock_locale():
    """Small mock of Locale object to make faster unit-tests."""
    mock = MagicMock()
    mock.code = 'en-US'
    yield mock


def test_tt_invalid_translation(mock_locale):
    """
    Check if translate toolkit returns errors if chek
    """
    assert quality_check(
        'Original string',
        'Translation \q',
        mock_locale,
    ) == {
        'ttWarnings': ['Escapes']
    }


def test_tt_disabled_checks(mock_locale):
    """
    Disabled checks should be respected by the quality_check.
    """
    assert quality_check(
        'Original string',
        'Translation \q',
        mock_locale,
        disabled_checks={'escapes'}
    ) == {}


def test_tt_correct_translation(mock_locale):
    """
    Quality check should return empty dictionary if everything is okay (no warnings).
    """
    assert quality_check(
        'Original string',
        'Translation string',
        mock_locale
    ) == {}