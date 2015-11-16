from django.core.management.base import BaseCommand, CommandError

import logging
from pontoon.base.models import Project
from pontoon.translation_memory.tasks import sync_translation_memory

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = '<project_slug project_slug ...>'
    help = 'Synchronize translation memory.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            dest='sync_all',
            default=False,
            help='Synchronize translation memory of all projects.'
        )

    def handle(self, *args, **options):
        """
        Synchronize project translations with translation memory
        """
        projects = Project.objects.filter(disabled=False)
        if args:
            projects = projects.filter(slug__in=args)

        projects = projects.values_list('pk', 'slug')

        if projects.exists() and not options['sync_all']:
            raise CommandError('No matching projects found.')

        for pk, slug in projects:
            log.info("Scheduled sync of translations for project: {}".format(slug))
            # @TODO: use delay()
            sync_translation_memory(pk)
