# coding: utf8
from urllib.parse import urlencode
from flask import escape

from flask import current_app, url_for

from labonneboite.conf import settings
from labonneboite.common import mapping as mapping_util
from labonneboite.common.email_util import MandrillClient
from labonneboite.common.models import Office, OfficeAdminAdd, OfficeAdminRemove, OfficeAdminUpdate
from labonneboite.common import models
from labonneboite.web.contact_form import forms

def compute_action_name(form):
    form_to_action = {
        'OfficeUpdateCoordinatesForm': 'Mise à jour des coordonnées',
        'OfficeUpdateJobsForm': 'Mise à jour des métiers',
        'OfficeRemoveForm': 'Suppression de coordonnées',
        'OfficeOtherRequestForm': 'Demande autre',
    }
    return form_to_action.get(form.__class__.__name__, 'Inconnu')


def common_mail_template(form):
    return """
        Un email a été envoyé par le formulaire de contact de la Bonne Boite :<br>
        - Action : {}<br>
        - Siret : {},<br>
        - Prénom : {},<br>
        - Nom : {}, <br>
        - E-mail : {},<br>
        - Téléphone : {},<br>
        <hr>
    """.format(
        compute_action_name(form),
        escape(form.siret.data),
        escape(form.first_name.data),
        escape(form.last_name.data),
        escape(form.email.data),
        escape(form.phone.data),
    )


def send_mail(mail_content):
    client = MandrillClient(current_app.extensions['mandrill'])
    client.send(mail_content)


def generate_update_coordinates_mail(form, recruiter_message):
    return """
        {}

        Nouveau site Internet : {}<br>
        Nouvel e-mail recruteur : {}<br>
        Nouveau téléphone : {}<br>

        Mode de contact à privilégier : {}<br>

        Nouvel email recruteur spécifique alternance : {}<br>
        Nouveau téléphone spécifique alternance : {}<br>
        Réseau social : {}<br>

        <hr>{}<hr>
        Cordialement,<br>
        La Bonne Boite & La Bonne alternance
    """.format(
        common_mail_template(form),

        escape(form.new_website.data),
        escape(form.new_email.data),
        escape(form.new_phone.data),

        forms.CONTACT_MODES_LABELS.get(form.new_contact_mode.data, 'Inconnu'),

        escape(form.new_email_alternance.data),
        escape(form.new_phone_alternance.data),
        escape(form.social_network.data),
        make_save_suggestion(
            form,
            recruiter_message,
            models.UpdateCoordinatesRecruiterMessage.name
        ),
    )


def generate_update_jobs_mail(form, recruiter_message):
    office = Office.query.filter(Office.siret == form.siret.data).first()
    office_romes = [item.code for item in mapping_util.romes_for_naf(office.naf)]

    all_romes, lbb_romes, lba_romes, hide_romes = forms.compute_romes()

    return """
        {}
        <br>
        Intéressé par des candidatures : <ul>{}</ul><br>
        Pas intéressé par des candidatures : <ul>{}</ul><br>
        Romes à ajouter LBB : <ul>{}</ul><br>
        <hr>
        Ouvert aux contrats d'alternance : <ul>{}</ul><br>
        Non ouvert à l'alternance : <ul>{}</ul><br>
        Romes à ajouter LBA : <ul>{}</ul><br>
        <hr>
        Romes à retirer : <ul>{}</ul><br>
        <hr>{}<hr>
        Cordialement,<br>
￼        La Bonne Boite & La Bonne alternance
    """.format(
        common_mail_template(form),
        # LBB
        format_romes(lbb_romes),
        format_romes(set(all_romes) - set(lba_romes)),
        format_romes(set(lbb_romes) - set(office_romes)),
        # LBA
        format_romes(lba_romes),
        format_romes(set(all_romes) - set(lbb_romes)),
        format_romes(set(lba_romes) - set(office_romes)),
        # Remove
        format_romes(hide_romes),
        make_save_suggestion(
            form,
            recruiter_message,
            models.UpdateJobsRecruiterMessage.name
        ),
    )


def format_romes(romes):
    """
    Return all romes has a HTMl list : <li>ROME_NAME (ROME_CODE)</li>
    """
    return ''.join(['<li>{} ({})</li>'.format(settings.ROME_DESCRIPTIONS[rome], rome) for rome in romes])


def generate_delete_mail(form, recruiter_message):
    return """
        {}

        Suppression de LBB : {}<br>
        Suppression de LBA : {}<br>

        <hr>{}<hr>
        Cordialement,<br>
        La Bonne Boite & La Bonne alternance
    """.format(
        common_mail_template(form),
        'oui' if form.remove_lbb.data else 'non',
        'oui' if form.remove_lba.data else 'non',
        make_save_suggestion(
            form,
            recruiter_message,
            models.RemoveRecruiterMessage.name,
        ),
    )


def generate_other_mail(form, recruiter_message):
    return """
        {}
        - Commentaire : {}<br>

        <hr>{}<hr>
        Cordialement,<br>
        La Bonne Boite & La Bonne alternance
    """.format(
        common_mail_template(form),
        escape(form.comment.data),
        make_save_suggestion(
            form,
            recruiter_message,
            models.OtherRecruiterMessage.name,
        ),
    )



def make_save_suggestion(form, recruiter_message, recruiter_message_type):
    # Save informations
    company = Office.query.filter_by(siret=form.siret.data).first()

    params = {
        'recruiter_message_id': recruiter_message.id,
        'recruiter_message_type': recruiter_message_type,
    }

    if not company:
        # OfficeAdminRemove already exits ?
        office_admin_remove = OfficeAdminRemove.query.filter_by(siret=form.siret.data).first()
        if office_admin_remove:
            url = url_for("officeadminremove.edit_view", id=office_admin_remove.id, _external=True, **params)
            return "Entreprise retirée via Save : <a href='{}'>Voir la fiche de suppression</a>".format(url)

        return 'Aucune entreprise trouvée avec le siret {}'.format(form.siret.data)

    # OfficeAdminAdd already exists ?
    office_admin_add = OfficeAdminAdd.query.filter_by(siret=form.siret.data).first()
    if office_admin_add:
        url = url_for("officeadminadd.edit_view", id=office_admin_add.id, _external=True, **params)
        return "Entreprise créée via Save : <a href='{}'>Voir la fiche d'ajout</a>".format(url)

    # OfficeAdminUpdate already exits ?
    office_admin_update = OfficeAdminUpdate.query.filter(
        OfficeAdminUpdate.sirets.like("%{}%".format(form.siret.data))
    ).first()

    if office_admin_update:
        url = url_for("officeadminupdate.edit_view", id=office_admin_update.id, _external=True, **params)
        return "Entreprise modifiée via Save : <a href='{}'>Voir la fiche de modification</a>".format(url)

    # No office AdminOffice found : suggest to create an OfficeAdminRemove
    url = url_for('officeadminupdate.create_view', _external=True, **params)
    return "Entreprise non modifiée via Save : <a href='{}'>Créer une fiche de modification</a>".format(url)