from rest_framework import viewsets
from .serializers import (
    InstitutionInstitutionSerializer, PersonInstitutionSerializer,
    PersonPlaceSerializer, PersonPersonSerializer, PersonEventSerializer, PersonWorkSerializer,
    InstitutionPlaceSerializer, InstitutionEventSerializer, InstitutionWorkSerializer, PlaceEventSerializer,
    PlaceWorkSerializer, PlacePlaceSerializer, EventWorkSerializer, EventEventSerializer, WorkWorkSerializer)
from .models import (InstitutionInstitution, PersonInstitution, PersonPlace, PersonPerson, PersonEvent, PersonWork,
                     InstitutionPlace, InstitutionEvent, InstitutionWork, EventWork, EventEvent, PlaceEvent, PlaceWork,
                     PlacePlace, WorkWork)
from apis_core.apis_entities.api_views import StandardResultsSetPagination


class InstitutionInstitutionViewSet(viewsets.ModelViewSet):
    queryset = InstitutionInstitution.objects.all()
    serializer_class = InstitutionInstitutionSerializer
    depth = 2
    filter_fields = ('related_institutionA__name', 'related_institutionB__name')


class PersonInstitutionViewSet(viewsets.ModelViewSet):
    queryset = PersonInstitution.objects.all()
    serializer_class = PersonInstitutionSerializer
    depth = 2
    filter_fields = ('related_person__name', 'related_institution__name')


class PersonPlaceViewSet(viewsets.ModelViewSet):
    queryset = PersonPlace.objects.all()
    serializer_class = PersonPlaceSerializer
    depth = 2
    filter_fields = ('related_place__name', 'related_person__name')


class PersonPersonViewSet(viewsets.ModelViewSet):
    queryset = PersonPerson.objects.all()
    serializer_class = PersonPersonSerializer
    depth = 2
    filter_fields = ('related_personA__name', 'related_personB__name')


class PersonEventViewSet(viewsets.ModelViewSet):
    queryset = PersonEvent.objects.all()
    serializer_class = PersonEventSerializer
    depth = 2
    filter_fields = ('related_person__name', 'related_event__name')


class PersonWorkViewSet(viewsets.ModelViewSet):
    queryset = PersonWork.objects.all()
    serializer_class = PersonWorkSerializer
    depth = 2
    filter_fields = ('related_person__name', 'related_work__name')


class InstitutionPlaceViewSet(viewsets.ModelViewSet):
    queryset = InstitutionPlace.objects.all()
    serializer_class = InstitutionPlaceSerializer
    depth = 2
    filter_fields = ('related_institution__name', 'related_place__name')


class InstitutionEventViewSet(viewsets.ModelViewSet):
    queryset = InstitutionEvent.objects.all()
    serializer_class = InstitutionEventSerializer
    depth = 2
    filter_fields = ('related_institution__name', 'related_event__name')


class InstitutionWorkViewSet(viewsets.ModelViewSet):
    queryset = InstitutionWork.objects.all()
    serializer_class = InstitutionWorkSerializer
    depth = 2
    filter_fields = ('related_institution__name', 'related_work__name')


class EventWorkViewSet(viewsets.ModelViewSet):
    queryset = EventWork.objects.all()
    serializer_class = EventWorkSerializer
    depth = 2
    filter_fields = ('related_event__name', 'related_work__name')


class EventEventViewSet(viewsets.ModelViewSet):
    queryset = EventEvent.objects.all()
    serializer_class = EventEventSerializer
    depth = 2
    filter_fields = ('related_eventA__name', 'related_eventB__name')


class PlaceEventViewSet(viewsets.ModelViewSet):
    queryset = PlaceEvent.objects.all()
    serializer_class = PlaceEventSerializer
    depth = 2
    filter_fields = ('related_place__name', 'related_event__name')


class PlaceWorkViewSet(viewsets.ModelViewSet):
    queryset = PlaceWork.objects.all()
    serializer_class = PlaceWorkSerializer
    depth = 2
    filter_fields = ('related_place__name', 'related_work__name')


class PlacePlaceViewSet(viewsets.ModelViewSet):
    queryset = PlacePlace.objects.all()
    serializer_class = PlacePlaceSerializer
    depth = 2
    filter_fields = ('related_placeA__name', 'related_placeB__name')


class WorkWorkViewSet(viewsets.ModelViewSet):
    queryset = WorkWork.objects.all()
    serializer_class = WorkWorkSerializer
    depth = 2
    filter_fields = ('related_workA__name', 'related_workB__name')
