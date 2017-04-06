import os
import logging

from django.core.management.base import BaseCommand, CommandError

from pontoon.terminology.formats import tbx
from pontoon.terminology.models import Term

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import .tbx (terminology) files into Pontoon.'
    format_handlers = {
        '.tbx': tbx,
    }

    def add_arguments(self, parser):
        parser.add_argument('files', nargs='+', type=str)

    def handle(self, *files, **options):
        terms = []
        files = options.get('files', [])

        for term_file in files:
            file_ext = os.path.splitext(term_file)[1].lower()
            if file_ext not in self.format_handlers:
                raise CommandError("Unrecognized file-extension: {}".format(file_ext))

            parser = self.format_handlers[file_ext]

            with open(term_file, "rU") as f:
                log.info('Parsing {} file: {}'.format(file_ext, term_file))
                terms.extend(tbx.parse_terms(f.read()))

        log.info('Loaded {} terms.'.format(len(terms)))

        Term.objects.import_vcs_terms(terms)
