# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This file has been copied from http://github.com/mozilla/testpilot
# and has been modified in order to use Fxa provider from the allauth package.
import os

from urlparse import urlparse, urljoin

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

from pontoon.base.models import Project, User


class Command(BaseCommand):
    help = 'Setup an instance of Pontoon deployed via Heroku Deploy.'

    def handle(self, *args, **options):
        app_host = urlparse(os.environ.get('SITE_URL')).netloc
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')

        User.objects.create_superuser(admin_email, admin_email, admin_password)
        Site.objects.filter(pk=1).update(name=app_host, domain=app_host)

        Project.objects.filter(slug='pontoon-intro').update(
            urljoin(app_host, 'introh')
        )
