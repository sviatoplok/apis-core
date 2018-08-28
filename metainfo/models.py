from django.db import models
#from reversion import revisions as reversion
import reversion
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from vocabularies.models import CollectionType, TextType, LabelType
from labels.models import Label
from .validators import date_validator

from datetime import datetime
import re
import unicodedata
from difflib import SequenceMatcher
#from helper_functions.highlighter import highlight_text

if 'apis_highlighter' in settings.INSTALLED_APPS:
    from apis_highlighter.models import Annotation


@reversion.register()
class TempEntityClass(models.Model):
    """ Base class to bind common attributes to many classes.

    The common attributes are:
    written start and enddates
    recognized start and enddates which are derived by RegEx
    from the written dates.
    A review boolean field to mark an object as reviewed
    """
    name = models.CharField(max_length=255, blank=True)
    review = models.BooleanField(
        default=False,
        help_text="Should be set to True, if the data record holds up quality standards.")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    start_date_written = models.CharField(
        max_length=255, blank=True, null=True,
        validators=[date_validator, ], verbose_name="Start",
        help_text="Please enter a date (DD).(MM).YYYY")
    end_date_written = models.CharField(
        max_length=255, blank=True, null=True,
        validators=[date_validator, ], verbose_name="End",
        help_text="Please enter a date (DD).(MM).YYYY")
    text = models.ManyToManyField("Text", blank=True)
    collection = models.ManyToManyField("Collection")
    status = models.CharField(max_length=100)
    source = models.ForeignKey('Source', blank=True, null=True,
                               on_delete=models.SET_NULL)
    references = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.name != "" and hasattr(self, 'first_name'):  # relation usually don´t have names
            return "{}, {}".format(self.name, self.first_name)
        elif self.name != "":
            return self.name
        else:
            return "(ID: {})".format(self.id)

    def save(self, *args, **kwargs):
        """Adaption of the save() method of the class to automatically parse string-dates into date objects
        """
        def match_date(date):
            """Function to parse string-dates into python date objects.
            """
            date = date.strip()
            date = date.replace('-', '.')
            if re.match(r'[0-9]{4}$', date):
                dr = datetime.strptime(date, '%Y')
                dr2 = date
            elif re.match(r'[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4}$', date):
                dr = datetime.strptime(date, '%d.%m.%Y')
                dr2 = date
            elif re.match(r'[0-9]{4}\.\.\.$', date):
                dr = datetime.strptime(date, '%Y...')
                dr2 = re.match(r'([0-9]{4})\.\.\.$', date).group(1)
            elif re.match(r'[0-9]{4}\.[0-9]{1,2}\.\.$', date):
                dr = datetime.strptime(date, '%Y.%m..')
                dr2 = re.match(r'([0-9]{4})\.([0-9]{1,2})\.\.$', date).group(2)
                +'.'+re.match(r'([0-9]{4})\.([0-9]{1,2})\.\.$', date).group(1)
            elif re.match(r'[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}$', date):
                dr = datetime.strptime(date, '%Y.%m.%d')
                dr3 = re.match(r'([0-9]{4})\.([0-9]{1,2})\.([0-9]{1,2})$', date)
                dr2 = dr3.group(3)+'.'+dr3.group(2)+'.'+dr3.group(1)
            elif re.match(r'^\s*$', date):
                dr = None
                dr2 = None
            else:
                dr = None
                dr2 = date
            return dr, dr2
        if self.start_date_written:
            self.start_date, self.start_date_written = match_date(self.start_date_written)
        else:
            self.start_date = self.start_date_written = None
        if self.end_date_written:
            self.end_date, self.end_date_written = match_date(self.end_date_written)
        else:
            self.end_date = self.end_date_written = None
        if self.name:
            self.name = unicodedata.normalize('NFC', self.name)
        super(TempEntityClass, self).save(*args, **kwargs)
        return self

    def merge_with(self, entities):
        e_a = type(self).__name__
        self_model_class = ContentType.objects.get(
            app_label='entities',
            model__iexact=e_a).model_class()
        if isinstance(entities, int):
            entities = self_model_class.objects.get(pk=entities)
        if not isinstance(entities, list):
            entities = [entities]
        entities = [self_model_class.objects.get(pk=ent) if type(ent) == int else ent for ent in entities]
        rels = ContentType.objects.filter(
            app_label='relations', model__icontains=e_a)
        print(rels)
        for ent in entities:
            e_b = type(ent).__name__
            if e_a != e_b:
                continue
            print(e_b)
            print(str(ent))
            lt, created = LabelType.objects.get_or_create(name='Legacy name (merge)')
            l_uri, created = LabelType.objects.get_or_create(name='Legacy URI (merge)')
            Label.objects.create(label=str(ent), label_type=lt, temp_entity=self)
            for u in Uri.objects.filter(entity=ent):
                Label.objects.create(label=str(u.uri), label_type=l_uri, temp_entity=self)
            for l in Label.objects.filter(temp_entity=ent):
                l.temp_entity = self
                l.save()
            for r in rels.filter(model__icontains=e_b):
                lst_ents_rel = str(r).split()
                if lst_ents_rel[0] == lst_ents_rel[1]:
                    q_d = {'related_{}A'.format(e_b.lower()): ent}
                    k = r.model_class().objects.filter(**q_d)
                    for t in k:
                        setattr(t, 'related_{}A'.format(e_a.lower()), self)
                        t.save()
                    q_d = {'related_{}B'.format(e_b.lower()): ent}
                    k = r.model_class().objects.filter(**q_d)
                    for t in k:
                        setattr(t, 'related_{}B'.format(e_a.lower()), self)
                        t.save()
                else:
                    q_d = {'related_{}'.format(e_b.lower()): ent}
                    k = r.model_class().objects.filter(**q_d)
                    for t in k:
                        setattr(t, 'related_{}'.format(e_a.lower()), self)
                        t.save()
            ent.delete()


@reversion.register()
class Source(models.Model):
    """ Holds information about entities and their relations"""
    orig_filename = models.CharField(max_length=255, blank=True)
    indexed = models.BooleanField(default=False)
    pubinfo = models.CharField(max_length=400, blank=True)
    author = models.CharField(max_length=255, blank=True)
    orig_id = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        if self.author != "" and self.orig_filename != "":
            return "{}, stored by {}".format(
                self.orig_filename, self.author)
        else:
            return "(ID: {})".format(self.id)


@reversion.register()
class Collection(models.Model):
    """ Allows to group entities and relation. """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    collection_type = models.ForeignKey(CollectionType, blank=True, null=True,
                                        on_delete=models.SET_NULL)
    groups_allowed = models.ManyToManyField(Group)
    parent_class = models.ForeignKey('self', blank=True, null=True,
                                     on_delete=models.CASCADE)

    def __str__(self):
        return self.name


@reversion.register()
class Text(models.Model):
    """ Holds unstructured text associeted with
    one ore many entities/relations. """

    kind = models.ForeignKey(TextType, blank=True, null=True,
                             on_delete=models.SET_NULL)
    text = models.TextField(blank=True)
    source = models.ForeignKey(Source, blank=True, null=True,
                               on_delete=models.SET_NULL)

    def __str__(self):
        if self.text != "":
            return "ID: {} - {}".format(self.id, self.text[:25])
        else:
            return "ID: {}".format(self.id)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            orig = Text.objects.get(pk=self.pk)
            if orig.text != self.text and 'apis_highlighter' in settings.INSTALLED_APPS:
                ann = Annotation.objects.filter(text_id=self.pk).order_by('start')
                seq = SequenceMatcher(None, orig.text, self.text)
                for a in ann:
                    changed = False
                    count = 0
                    for s in seq.get_matching_blocks():
                        count += 1
                        if s.a <= a.start and (s.a + s.size) >= a.end:
                            a.start += (s.b - s.a)
                            a.end += (s.b - s.a)
                            a.save()
                            changed = True
                    if not changed:
                        a.delete()  # TODO: we might want to delete relations as well.
        super().save(*args, **kwargs)


@reversion.register()
class Uri(models.Model):
    uri = models.URLField(blank=True, null=True, unique=True, max_length=255)
    domain = models.CharField(max_length=255, blank=True)
    rdf_link = models.URLField(blank=True)
    entity = models.ForeignKey(TempEntityClass, blank=True, null=True,
                               on_delete=models.CASCADE)
    # loaded set to True when RDF was loaded and parsed into the data model
    loaded = models.BooleanField(default=False)
    # Timestamp when file was loaded and parsed
    loaded_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.uri

    def get_web_object(self):
        result = {
            'relation_pk': self.pk,
            'relation_type': 'uri',
            'related_entity': self.entity.name,
            'uri': self.uri,
            }
        return result


@reversion.register()
class UriCandidate(models.Model):
    """Used to store the URI candidates for automatically generated entities.
    """
    uri = models.URLField()
    confidence = models.FloatField(blank=True, null=True)
    responsible = models.CharField(max_length=255)
    entity = models.ForeignKey(TempEntityClass, blank=True, null=True,
                               on_delete=models.CASCADE)


@receiver(post_save, sender=Uri, dispatch_uid="remove_default_uri")
def remove_default_uri(sender, instance, **kwargs):
    if Uri.objects.filter(entity=instance.entity).count() > 1:
        Uri.objects.filter(entity=instance.entity, domain='apis default').delete()
