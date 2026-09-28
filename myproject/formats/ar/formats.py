# Django's Arabic formats don't group thousands (516500). Egyptian sites write 516,500,
# so keep Django's Arabic dates and override only the number formatting.
from django.conf.locale.ar.formats import *  # noqa: F401,F403

DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3
