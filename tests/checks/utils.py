import json

import pytest

from textwrap import dedent
from mock import patch, MagicMock, ANY

from pontoon.checks.utils import get_quality_checks


@pytest.yield_fixture
def tt_quality_check_mock():
    with patch('pontoon.checks.utils.translate_toolkit.quality_check') as mock:
        yield mock


@pytest.yield_fixture()
def entity_properties_mock():
    """
    Mock of entity from a .properties file.
    """
    mock = MagicMock()
    mock.resource.path = 'file.properties'
    mock.resource.format = 'properties'
    mock.resource.all.return_value = []
    mock.string = 'Example string'

    yield mock


@pytest.yield_fixture()
def entity_invalid_resource_mock():
    """
    Mock of entity from a resource with unsupported filetype.
    """
    mock = MagicMock()
    mock.resource.path = 'file.invalid'
    mock.resource.format = 'invalid'
    mock.resource.all.return_value = []
    mock.string = 'Example string'

    yield mock


@pytest.yield_fixture()
def entity_ftl_mock():
    """
    Mock of entity from a  a .ftl file.
    """
    mock = MagicMock()
    mock.resource.path = 'file.ftl'
    mock.resource.format = 'ftl'
    mock.resource.all.return_value = []
    mock.string = dedent("""
    windowTitle = Untranslated string
        .pontoon = is cool
    """)

    yield mock


@pytest.yield_fixture()
def locale_mock():
    mock = MagicMock()
    mock.code = 'en-US'
    yield mock


def test_ignore_warnings(
        entity_ftl_mock,
        locale_mock
):
    """
    Check if logic of ignore_warnings works when there are errors.
    """
    assert get_quality_checks(
        entity_ftl_mock,
        locale_mock,
        0,
        dedent("""
        windowTitle = Translated string
            .pontoon = is cool
            .pontoon = is cool2
        """),
        False
    ).content == json.dumps({
        'checks': {
            'clWarnings': ['Attribute "pontoon" occurs 2 times'],
            'ttWarnings': ["Double spaces", "Newlines"]
        }
    })

    # Warnings can be ignored if user decides to do so
    assert get_quality_checks(
        entity_ftl_mock,
        locale_mock,
        0,
        dedent("""
        windowTitle = Translated string
            .pontoon = is cool
            .pontoon = is cool2
        """),
        True
    ) is None

    # Quality check should always return critical errors
    assert get_quality_checks(
        entity_ftl_mock,
        locale_mock,
        0,
        dedent("""
        windowTitle
            .pontoon = is cool
            .pontoon = is cool2
        """),
        True
    ).content == json.dumps({
        'checks': {
            'ttWarnings': ["Double spaces", "Newlines"],
            'clWarnings': ['Attribute "pontoon" occurs 2 times'],
            'clErrors': ["Missing value"],
        }
    })


def test_invalid_resource_compare_locales(
    entity_invalid_resource_mock,
    locale_mock,
):
    """
    Unsupported resource shouldn't raise an error.
    """
    assert get_quality_checks(
        entity_invalid_resource_mock,
        locale_mock,
        0,
        'Translation',
        False
    ) is None


def test_tt_disabled_checks(
    entity_ftl_mock,
    entity_properties_mock,
    locale_mock,
    tt_quality_check_mock
):
    """
    Check if overlapping checks are disabled in Translate Toolkit.
    """
    assert get_quality_checks(
        entity_properties_mock,
        locale_mock,
        0,
        'invalid translation \q',
        False
    ).content == json.dumps({
        'checks': {
            'clWarnings': [
                'unknown escape sequence, \q'
            ]
        }
    })

    tt_quality_check_mock.assert_called_with(
        ANY,
        ANY,
        ANY,
        {'escapes', 'nplurals', 'printf'}
    )

    assert get_quality_checks(
        entity_ftl_mock,
        locale_mock,
        0,
        dedent("""
        windowTitle = Translated string
            .pontoon = is cool
        """),
        False
    ) is None
    tt_quality_check_mock.assert_called_with(
        ANY,
        ANY,
        ANY,
        set()
    )
