import os
import requests
import sys
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand, CommandError

from pontoon.base.models import Locale


"""
Locale codes from Microsoft portal that can't be directly mapped to locales provided by Pontoon.
"""

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
    def ms_portal_locales(self):
        """Map of locales to form values, extracted from Microsoft Terminology Portal."""
        locales_map = {}

        for option in self.page.find('select', class_='terminology').findChildren('option'):
            value = option['value']
            locale_code = value.split('|')[1]
            locales_map[locale_code] = value
        return locales_map

    def download_terminology_file(self, path, locale_code, locale_form_value):
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
        ms_locale_code = locale_form_value.split('|')[1]
        with open(path, 'w') as f:
            file_content = file_data.content

            # Replace MS locale code with Pontoon code to make it easier to import.
            file_content = file_content.replace(
                'xml:lang="{}"'.format(ms_locale_code),
                'xml:lang="{}"'.format(locale_code)
            )
            f.write(file_content)

    def handle(self, *args, **options):
        locale_code = options.get('locale')
        output_dir = options.get('output_dir')

        if not output_dir:
            raise CommandError('You have to set output directory.')

        # A list of Pontoon locales that share terminology with Microsoft Portal.
        terminology_locales = (
            Locale
                .objects
                .filter(ms_terminology_code__isnull=False)
        )
        print 'Discovered {} available locales.'.format(len(self.ms_portal_locales))

        if locale_code:
            try:
                locales_to_download = [
                    terminology_locales.get(code=locale_code)
                ]
            except Locale.DoesNotExist:
                print "Can't find locale: {}".format(locale_code.lower())
                print "Available locales:"
                print ', '.join(sorted(terminology_locales.values_list('code', flat=True)))
                sys.exit()
        else:
            # Download all locales if no specific locale is requested.
            locales_to_download = terminology_locales

        for locale in locales_to_download:
            file_path = os.path.join(output_dir, '{}.tbx'.format(locale.code))

            print 'Downloading {} into {}'.format(locale_code, file_path)
            self.download_terminology_file(file_path, locale.code, self.ms_portal_locales[locale.ms_terminology_code])

