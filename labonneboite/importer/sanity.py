import logging
from sqlalchemy import and_

from labonneboite.importer.util import timeit
from labonneboite.importer import settings
from labonneboite.common.models import Office

logger = logging.getLogger('main')


@timeit
def check_scores(departements=settings.DEPARTEMENTS, minimum_office_count=100):
    errors = []
    for departement in departements:
        # FIXME point to etablissements_reduced instead of etablissements
        departement_count = Office.query.filter(
            and_(
                Office.departement == departement,
                Office.score > 50)).count()
        logger.debug("%i offices with score > 50 in departement %s", departement_count, departement)
        ok = departement_count >= minimum_office_count
        if not ok:
            errors.append(departement)
    return errors
