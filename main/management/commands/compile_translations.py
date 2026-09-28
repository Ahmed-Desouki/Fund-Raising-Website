"""
Compile locale/*/LC_MESSAGES/django.po into the .mo files Django reads.

Same job as Django's `compilemessages`, but in pure Python (polib), so it works on
machines without GNU gettext installed, e.g. a fresh Windows setup.
"""
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Compile the .po translation files into .mo files (no gettext needed)'

    def handle(self, *args, **options):
        for locale_dir in settings.LOCALE_PATHS:
            for po_path in Path(locale_dir).glob('*/LC_MESSAGES/*.po'):
                po = polib.pofile(str(po_path))
                po.save_as_mofile(str(po_path.with_suffix('.mo')))
                self.stdout.write(f'{po_path}: {len(po.translated_entries())} translated, '
                                  f'{len(po.untranslated_entries())} missing')
