"""
Recipient resolution: turning a NotificationRule + event context into a
list of concrete recipients. A recipient is never assumed to be a User -
it can be a Customer, Patient, Employee, Person, Contact, an explicit
email/phone, or anything a business app registers its own resolver for.
"""

from dataclasses import dataclass, field
from typing import Optional

from django_resaas.notifications.conditions import _MISSING, resolve_field


@dataclass
class Recipient:
    """A resolved recipient, channel-agnostic.

    `key` is the normalized identity used by NotificationPreference
    (e.g. "user:<uuid>", "person:<uuid>", "email:foo@bar.com").
    """

    type: str
    key: str
    email: Optional[str] = None
    phone: Optional[str] = None
    language_code: Optional[str] = None


@dataclass
class ResolverContext:
    payload: dict  # the raw EventDispatcher payload
    rule: "django_resaas.notifications.models.NotificationRule"  # noqa: F821
    obj: object = None  # the resolved business instance, or None
    actor: object = None  # the resolved actor (User), or None
    recipient_config: dict = field(default_factory=dict)


class RecipientResolverRegistry:
    """`register(key, resolver)` lets business apps add their own
    strategies (e.g. "sales.customer", "saude.patient") without touching
    django_resaas. `resolver(ctx: ResolverContext) -> list[Recipient]`."""

    _resolvers = {}

    @classmethod
    def register(cls, key, resolver):
        cls._resolvers[key] = resolver

    @classmethod
    def get(cls, key):
        return cls._resolvers.get(key)

    @classmethod
    def resolve(cls, key, ctx):
        resolver = cls.get(key)
        if resolver is None:
            return []
        return resolver(ctx) or []


# =================================================================
# HELPERS
# =================================================================


def _person_like_to_recipient(type_name, obj, id_attr="id"):
    if obj is None:
        return None

    email = getattr(obj, "email", None)
    phone = getattr(obj, "mobile", None) or getattr(obj, "phone", None)
    language = getattr(obj, "language", None)
    language_code = getattr(language, "code", None)

    if not email and not phone:
        return None

    return Recipient(
        type=type_name,
        key=f"{type_name}:{getattr(obj, id_attr)}",
        email=email,
        phone=phone,
        language_code=language_code,
    )


def _user_to_recipient(user):
    return _person_like_to_recipient("user", user)


# =================================================================
# BUILT-IN RESOLVERS
# =================================================================


def resolve_actor(ctx: ResolverContext):
    recipient = _user_to_recipient(ctx.actor)
    return [recipient] if recipient else []


def resolve_field_path(ctx: ResolverContext):
    path = ctx.recipient_config.get("field_path")
    if not path or ctx.obj is None:
        return []

    target = resolve_field(ctx.obj, path)
    if target is _MISSING or target is None:
        return []

    # A resolved User -> "user:<id>"; anything else with email/phone gets
    # a generic "object" identity so preferences can still key off it.
    recipient = _user_to_recipient(target) or _person_like_to_recipient(
        "object", target
    )
    return [recipient] if recipient else []


def resolve_object_owner(ctx: ResolverContext):
    # Same mechanism as field_path - "object_owner" is just the common,
    # more readable name for the same lookup.
    return resolve_field_path(ctx)


def resolve_explicit(ctx: ResolverContext):
    email = ctx.recipient_config.get("email")
    phone = ctx.recipient_config.get("phone")

    if not email and not phone:
        return []

    identity = email or phone

    return [
        Recipient(
            type="explicit",
            key=f"explicit:{identity}",
            email=email,
            phone=phone,
        )
    ]


def resolve_entity_admin(ctx: ResolverContext):
    entity = getattr(ctx.rule, "entity", None)
    if entity is None:
        return []

    # Entity.admins is the framework's own, real notion of "administrator
    # of this entity" (ResaasContextService.validate_entity uses the same
    # relation to grant automatic access) - reused as-is here.
    recipients = []
    for user in entity.admins.all():
        recipient = _user_to_recipient(user)
        if recipient:
            recipients.append(recipient)
    return recipients


def resolve_branch_admin(ctx: ResolverContext):
    """Best-effort: this framework has no explicit "branch admin" role
    today (BranchUser carries no admin flag). This resolver looks up
    users who hold a configurable permission (recipient_config
    ["permission"], default "change_branch") within the rule's branch via
    BranchUserGroup. Documented limitation - replace/override this
    resolver in modules that have a more precise notion of branch admin.
    """

    from django_resaas.engine.models.branch_user_group import BranchUserGroup

    branch = getattr(ctx.rule, "branch", None)
    if branch is None:
        return []

    permission_codename = ctx.recipient_config.get("permission", "change_branch")

    users = (
        BranchUserGroup.objects.filter(
            branch=branch,
            group__permissions__codename=permission_codename,
        )
        .values_list("user", flat=True)
        .distinct()
    )

    from django_resaas.engine.models.user import User

    recipients = []
    for user in User.objects.filter(id__in=list(users)):
        recipient = _user_to_recipient(user)
        if recipient:
            recipients.append(recipient)
    return recipients


RecipientResolverRegistry.register("actor", resolve_actor)
RecipientResolverRegistry.register("object_owner", resolve_object_owner)
RecipientResolverRegistry.register("field_path", resolve_field_path)
RecipientResolverRegistry.register("explicit", resolve_explicit)
RecipientResolverRegistry.register("entity_admin", resolve_entity_admin)
RecipientResolverRegistry.register("branch_admin", resolve_branch_admin)
