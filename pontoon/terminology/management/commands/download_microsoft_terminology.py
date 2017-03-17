import os
import requests
import sys
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand, CommandError


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
        with open(path, 'w') as f:
            f.write(file_data.content)

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
            file_path = os.path.join(output_dir, '{}.tbx'.format(locale_code))
            print 'Downloading {} into {}'.format(locale_code, file_path)
            self.download_terminology_file(file_path, locale_form_value)

        print 'Done!'

