"""Welcome email sent by the interactive bootstrap commands
(management/commands/create_root.py, create_entity.py) once the
superuser + Entity/EntityType/Branch have been created - confirms the
account/tenant by email and gives a few getting-started pointers.

Reuses the exact same email infrastructure as OTP/password-reset
(core/services/otp_service.py, core/utils/templates.py's
render_email_template(), NotificationProviderRegistry) - no second
notification path, no new template engine.

Never raises: create_root/create_entity are one-time, interactive
setup commands whose real job (creating the account) has already
succeeded by the time this runs. A missing/misconfigured email
provider must never make the command look like it failed - the
password/user/tenant already exist either way. Callers get a plain
True/False back to report on stdout.

Includes the password in the email (product decision) only when the
caller passes one in - i.e. only for a superuser that was actually
just created here, never for a pre-existing one whose real password
is unknown to this command."""
import logging

from django.conf import settings

from django_resaas.saas.core.utils.templates import render_email_template
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers import NotificationProviderRegistry

logger = logging.getLogger(__name__)


def send_bootstrap_welcome_email(user, *, entity=None, entity_type=None, branch=None, group=None, password=None):
    try:
        provider = NotificationProviderRegistry.get(Channel.EMAIL)

        if provider is None or not user.email:
            return False

        entity_name = getattr(entity, "name", None)

        logo_url = None
        if entity is not None and getattr(entity, "display_logo_login", True) and getattr(entity, "logo", None):
            try:
                logo_url = entity.logo.url
            except ValueError:
                logo_url = None

        # Sem request/origin (comando de terminal, não HTTP) não há como
        # saber com segurança o endereço público do frontend - só se
        # mostra o botão quando o projecto o configurou explicitamente,
        # nunca se inventa um URL.
        login_url = getattr(settings, "FRONTEND_URL", None)

        instructions = [
            Translate.tdc(None, "Sign in with the username and the password you just chose."),
            Translate.tdc(None, "Your account has full administrative (Root) access - invite your team and assign groups from the Users section."),
            Translate.tdc(None, "Review the Theme and Layout under Appearance before sharing access with anyone else."),
        ]

        html = render_email_template("BOOTSTRAP_WELCOME", {
            "entity_name": entity_name,
            "logo": logo_url,
            "greeting": Translate.tdc(None, "Welcome, {username}!").format(username=user.username),
            "intro": Translate.tdc(
                None,
                "Your RESAAS environment has been created successfully. Here is a summary of what was set up.",
            ),
            "username_label": Translate.tdc(None, "Username"),
            "username": user.username,
            "email_label": Translate.tdc(None, "Email"),
            "email": user.email,
            "password_label": Translate.tdc(None, "Password"),
            "password": password,
            "entity_label": Translate.tdc(None, "Entity"),
            "entity": entity_name,
            "branch_label": Translate.tdc(None, "Branch"),
            "branch": getattr(branch, "name", None),
            "group_label": Translate.tdc(None, "Group"),
            "group": getattr(group, "name", None) if not isinstance(group, str) else group,
            "instructions_title": Translate.tdc(None, "Getting started"),
            "instructions": instructions,
            "login_url": login_url,
            "button_label": Translate.tdc(None, "Open your workspace"),
            "security_notice": Translate.tdc(
                None,
                "For your security, please sign in and change this password as soon as possible.",
            ) if password else Translate.tdc(
                None,
                "This is an automated message confirming your account was created.",
            ),
            "footer_notice": Translate.tdc(None, "This is an automated message, please do not reply."),
        })

        plain_body = Translate.tdc(
            None, "Your RESAAS account ({email}) was created successfully. Username: {username}.",
        ).format(email=user.email, username=user.username)

        provider.send(
            recipient=user.email,
            subject=Translate.tdc(None, "Your RESAAS environment is ready"),
            body=plain_body,
            metadata={"html": html},
        )
        return True

    except Exception as exc:
        logger.warning("[bootstrap] welcome email not sent to %s: %s", getattr(user, "email", "?"), exc)
        return False
