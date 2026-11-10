from django.core.exceptions import ValidationError
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class BranchOpeningHours(TimeModel):
    """When a Branch is open: one row per interval of a weekday, so a day may
    have several (08:00-12:00 and 14:00-17:00) and a day with no row is
    closed. Generic: any business sets its units' hours; the health module's
    booking uses them when the doctor has no schedule of their own."""

    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    branch = models.ForeignKey("django_resaas.Branch", on_delete=models.CASCADE, related_name="opening_hours")
    weekday = models.IntegerField(choices=WEEKDAYS)
    opens_at = models.TimeField()
    closes_at = models.TimeField()

    class Meta:
        ordering = ["branch", "weekday", "opens_at"]
        verbose_name = "Branch opening hours"
        verbose_name_plural = "Branch opening hours"

    class RESAAS:
        label_field = "branch.name"
        crud = True

    def clean(self):
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError({"closes_at": "The closing time must be after the opening time."})

    def __str__(self):
        return f"{self.branch} {self.get_weekday_display()} {self.opens_at:%H:%M}-{self.closes_at:%H:%M}"


def open_intervals(branch_id, weekday):
    """[(opens_at, closes_at), ...] of the branch on that weekday, in order;
    [] when the branch has hours but none that day (closed); None when the
    branch has no hours at all (not configured)."""
    rows = BranchOpeningHours.objects.filter(branch_id=branch_id)
    if not rows.exists():
        return None
    return [(r.opens_at, r.closes_at) for r in rows.filter(weekday=weekday).order_by("opens_at")]
