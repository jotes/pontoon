import os
import requests
import sys
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand, CommandError

"""
Locale codes from Microsoft portal that can't be directly mapped to locales provided by Pontoon.
"""
LOCALES_MAP = {
    u'af-za': u'af',
    u'am-et': u'am',
    u'ar-sa': u'ar',
    u'as-in': u'as',
    u'be-by': u'be',
    u'bg-bg': u'bg',
    u'ca-es': u'ca',
    u'cs-cz': u'cs',
    u'cy-gb': u'cy',
    u'da-dk': u'da',
    u'de-de': u'de',
    u'el-gr': u'el',
    u'et-ee': u'et',
    u'eu-es': u'eu',
    u'fa-ir': u'fa',
    u'fi-fi': u'fi',
    u'fr-fr': u'fr',
    u'ga-ie': u'ga-IE',
    u'gl-es': u'gl',
    u'gu-in': u'gu-IN',
    u'ha-Latn-ng': u'ha',
    u'he-il': u'he',
    u'hi-in': u'hi-IN',
    u'hr-hr': u'hr',
    u'hu-hu': u'hu',
    u'hy-am': u'hy-AM',
    u'id-id': u'id',
    u'ig-ng': u'ig',
    u'is-is': u'is',
    u'it-it': u'it',
    u'ja-jp': u'ja',
    u'ka-ge': u'ka',
    u'kk-kz': u'kk',
    u'km-kh': u'km',
    u'kn-in': u'kn',
    u'ko-kr': u'ko',
    u'lo-la': u'lo',
    u'lt-lt': u'lt',
    u'lv-lv': u'lv',
    u'ml-in': u'ml',
    u'mr-in': u'mr',
    u'ne-np': u'ne-NP',
    u'nl-nl': u'nl',
    u'pa-in': u'pa-IN',
    u'pl-pl': u'pl',
    u'ro-ro': u'ro',
    u'ru-ru': u'ru',
    u'si-lk': u'si',
    u'sk-sk': u'sk',
    u'sl-si': u'sl',
    u'sq-al': u'sq',
    u'sv-se': u'sv-SE',
    u'te-in': u'te',
    u'th-th': u'th',
    u'tr-tr': u'tr',
    u'uk-ua': u'uk',
    u'ur-pk': u'ur',
    u'vi-vn': u'vi',
    u'wo-sn': u'wo',
    u'yo-ng': u'yo',

    # Locales that couldn't be directly mapped to the pontoon.
    u'az-Latn-az': u'',
    u'bn-bd': u'',
    u'bn-in': u'',
    u'bs-Cyrl-ba': u'',
    u'bs-Latn-ba': u'',
    u'ca-ES-valencia': u'',
    u'chr-Cher-US': u'',
    u'en-gb': u'',
    u'es-es': u'',
    u'es-mx': u'',
    u'fr-ca': u'',
    u'gd-gb': u'',
    u'guc-VE': u'',
    u'iu-Latn-ca': u'',
    u'kok-in': u'',
    u'ku-Arab-IQ': u'',
    u'ky-kg': u'',
    u'lb-lu': u'',
    u'mi-nz': u'',
    u'mk-mk': u'',
    u'mn-mn': u'',
    u'ms-bn': u'',
    u'ms-my': u'',
    u'mt-mt': u'',
    u'nb-no': u'',
    u'nn-no': u'',
    u'nso-za': u'',
    u'or-in': u'',
    u'pa-Arab-PK': u'',
    u'prs-AF': u'',
    u'ps-af': u'',
    u'pt-br': u'',
    u'pt-pt': u'',
    u'quc-Latn-GT': u'',
    u'quz-pe': u'',
    u'rw-rw': u'',
    u'sd-Arab-PK': u'',
    u'sr-Cyrl-ba': u'',
    u'sr-Cyrl-rs': u'',
    u'sr-Latn-rs': u'',
    u'sw-ke': u'',
    u'ta-in': u'',
    u'tg-Cyrl-tj': u'',
    u'ti-et': u'',
    u'tk-tm': u'',
    u'tl-PH': u'',
    u'tn-za': u'',
    u'tt-ru': u'',
    u'ug-cn': u'',
    u'uz-Latn-uz': u'',
    u'xh-za': u'',
    u'zh-cn': u'',
    u'zh-hk': u'',
    u'zh-tw': u'',
    u'zu-za': u''
 }

class Command(BaseCommand):
    help = 'Download all or selected terminology files from the Microsoft Language Portal.'

    TERMINOLOGY_URL = 'https://www.microsoft.com/Language/en-US/Terminology.aspx'

    def add_arguments(self, parser):
        parser.add_argument('--locale', help='If you pass specific locale, script will download only one file.')
        parser.add_argument('--output-dir', default='.', help='A directory which will store terminology files.'),

    @property
    def page(self):
        """Returns ready to use BS object with contents of the terminology page."""
        return BeautifulSoup(requests.get(self.TERMINOLOGY_URL).content, 'html.parser')

    @property
    def available_locales(self):
        """Map of locale codes and their respective form values."""
        locales_map = {}

        for option in self.page.find('select', class_='terminology').findChildren('option'):
            value = option['value']
            locale_code = value.split('|')[1]
            locales_map[locale_code] = value
        return locales_map

    def download_terminology_file(self, path, locale_form_value):
        # Because it's an ASP.NET page we have to extract viewstate and eventvalidation from the page first.
        viewstate = self.page.find(id="__VIEWSTATE")['value']
        eventvalidation = self.page.find(id="__EVENTVALIDATION")['value']
        file_data = requests.post(self.TERMINOLOGY_URL, {
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$lnk_modalDownload',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': '',
            '__EVENTVALIDATION': eventvalidation,
            'ctl00$mslSearchControl$txt_SearchControl': '',
            'ctl00$cbo_LocSites': '0',
            'ctl00$ContentPlaceHolder1$lb_Lang': locale_form_value
        })
        locale_code = locale_form_value.split('|')[1]
        with open(path, 'w') as f:
            file_content = file_data.content
            # Translate locale code for easier processing later.
            file_content = file_content.replace(
                'xml:lang="{}"'.format(locale_code),
                'xml:lang="{}"'.format(LOCALES_MAP[locale_code])
            )
            f.write(file_content)

    def handle(self, *args, **options):
        locale = options.get('locale')
        output_dir = options.get('output_dir')

        if not output_dir:
            raise CommandError('You have to set output directory.')

        available_locales = self.available_locales
        print 'Discovered {} available locales.'.format(len(available_locales))

        if locale:
            try:
                locales_to_download = {locale.lower(): available_locales[locale.lower()]}
            except KeyError:
                print "Can't find locale: {}".format(locale.lower())
                print "Available locales:"
                print ', '.join(sorted(available_locales))
                sys.exit()
        else:
            locales_to_download = available_locales

        for locale_code, locale_form_value in locales_to_download.items():
            file_path = os.path.join(output_dir, '{}.tbx'.format(LOCALES_MAP[locale_code]))
            print 'Downloading {} into {}'.format(locale_code, file_path)
            self.download_terminology_file(file_path, locale_form_value)

