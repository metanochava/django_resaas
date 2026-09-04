# hr/views/review_competency_rating.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.review_competency_rating import ReviewCompetencyRating
from django_resaas.hr.serializers.review_competency_rating import (
    ReviewCompetencyRatingSerializer,
)


@registerView('reviewcompetencyratings', module='hr')
class ReviewCompetencyRatingAPIView(BaseAPIView):
    queryset = ReviewCompetencyRating.objects.all()
    serializer_class = ReviewCompetencyRatingSerializer
