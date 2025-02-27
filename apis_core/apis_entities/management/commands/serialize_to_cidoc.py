from django.core.management.base import BaseCommand, CommandError
from apis_core.apis_entities.models import Person
from django.contrib.contenttypes.models import ContentType
from apis_core.apis_entities.serializers_generic import EntitySerializer
from apis_core.apis_entities.api_renderers import EntityToCIDOC
from apis_core.apis_vocabularies.serializers import GenericVocabsSerializer
from apis_core.apis_vocabularies.api_renderers import VocabToSkos
import json
import pickle
from django.conf import settings
import requests
from rdflib import Graph
from rdflib.plugins.memory import IOMemory
from SPARQLWrapper import SPARQLWrapper, POST, BASIC, JSON

map_ct = {
    'trig': ('application/x-trig', 'trig'),
    'trix': ('application/trix', 'trix'),
    'xml': ('application/rdf+xml', 'xml'),
    'turtle': ('application/x-turtle', 'ttl'),
    'n3': ('text/rdf+n3', 'n3')
}

base_uri = getattr(settings, 'APIS_BASE_URI', 'http://apis.info')
if base_uri.endswith('/'):
    base_uri = base_uri[:-1]


class Command(BaseCommand):
    help = 'Command to serialize APIS data to cidoc and update a triple store.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filter',
            action='store',
            dest='filter',
            default="{}",
            help='Specify a dictionary of filter arguments for the Entity queryset.',
        )

        parser.add_argument(
            '--entity',
            action='store',
            dest='entity',
            default='Person',
            help='Specify a dictionary of filter arguments for the Person queryset.',
        )

        parser.add_argument(
            '--update',
            action='store_true',
            dest='update',
            default=False,
            help='Use to update triple store (needs credentials).',
        )

        parser.add_argument(
            '--triple-store',
            action='store',
            dest='triplestore',
            default=False,
            help='Specify a tuple of URL, username, password to access triple-store.',
        )

        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=True,
            help='Use to delete the named graph before inserting (defaults to True).',
        )

        parser.add_argument(
            '--named-graph',
            action='store',
            dest='namedgraph',
            default=False,
            help='Uri of named graph to use.',
        )

        parser.add_argument(
            '--output',
            action='store',
            dest='output',
            default=False,
            help='Path of file to store RDF in.',
        )

        parser.add_argument(
            '--update-vocabs',
            action='store_true',
            dest='update-vocabs',
            default=False,
            help='Specify whether to update skosmos vocabularies (needs settings in place).',
        )

        parser.add_argument(
            '--format',
            action='store',
            dest='format',
            default='xml',
            help='Format to use (xml, trig, n3, turtle, nquads, trix).',
        )

    def handle(self, *args, **options):
        ent = ContentType.objects.get(app_label="apis_entities", model=options['entity']).model_class()
        res = []
        objcts = ent.objects.filter(**json.loads(options['filter']))
        if objcts.filter(uri__uri__icontains=' ').count() > 0:
            self.stdout.write(self.style.ERROR('URIs found that contain whitespaces'))
            return
        if objcts.count() > 1000:
            self.stdout.write(self.style.NOTICE('More than 1000 objects, caching'))
            cnt = 0
            while (cnt * 1000) < objcts.count():
                r = []
                for e in objcts[1000*cnt:(1000*cnt+1000)]:
                    r.append(EntitySerializer(e).data)
                with open(f'serializer_cache/{cnt}.pkl', 'wb') as out:
                    pickle.dump(r, out)
                    self.stdout.write(self.style.NOTICE(f'Pickle written to: serializer_cache/{cnt}.pkl'))
                cnt += 1
            res = '/home/sennierer/projects/apis-webpage-base/serializer_cache'
        else:
            for e in objcts:
                res.append(EntitySerializer(e).data)

        self.stdout.write(self.style.SUCCESS(f'serialized {len(res)} objects'))
        self.stdout.write(self.style.NOTICE('Starting to create the graph'))
        store = IOMemory()
        fin, store = EntityToCIDOC().render(res, format_1=options['format'], store=store, binary=True, named_graph=options['namedgraph'])
        if options['update-vocabs']:
            self.stdout.write(self.style.NOTICE('Starting to create the SKOS vocabs.'))
            for v in ContentType.objects.filter(app_label="apis_vocabularies").exclude(model__in=["vocabnames"]):
                v_res = v.model_class().objects.all()
                if v_res.count() > 0:
                    v_res_ser = GenericVocabsSerializer(v_res, many=True).data
                    fin = VocabToSkos().render(v_res_ser, g=fin)
        if options['output']:
            with open(options['output'], 'wb') as out:
                out.write(fin.serialize(format=options['format']))
            self.stdout.write(self.style.SUCCESS(f'Wrote file to {options["output"]}'))
        if options['update']:
            if not options['triplestore']:
                url, username, password = getattr(settings, 'APIS_BLAZEGRAPH', (False, False, False))
                if not url:
                    self.stdout.write(self.style.ERROR('When asking for update you need to either specify settings in APIS_BLAZEGRAPH or in the management command (--triple-store)'))
                    return
            else:
                url, username, password = options['triplestore']
                if not url or not username or not password:
                    self.stdout.write(self.style.ERROR('Missing some settings for Triplestore update'))
                    return
            sparql_serv = SPARQLWrapper(url)
            sparql_serv.setHTTPAuth(BASIC)
            sparql_serv.setCredentials(username, password)
            sparql_serv.setMethod(POST)
            sparql_serv.setReturnFormat(JSON)
            sp_count = f"""
                    SELECT (COUNT(*) AS ?triples)
                    FROM <{base_uri}/entities#>
                    WHERE {{ ?s ?p ?o }}
                    """
            if options['delete']:
                if not options['namedgraph']:
                    sparql_serv.setQuery(sp_count)
                    res_count_1 = sparql_serv.query().convert()
                    count = int(res_count_1['results']['bindings'][0]['triples']['value'])
                    if count > 0:
                        self.stdout.write(self.style.NOTICE(f'Found {count} triples in named graph >> deleting'))
                    params = {'c': f'<{base_uri}/entities#>'}
                    res3 = requests.delete(url, auth=(username, password), headers={'Accept': 'application/xml'}, params=params)
                    self.stdout.write(self.style.NOTICE(f'Deleted the graph: {res3.text} {res3.status_code}'))
                    for f in ['class', 'property']:
                        sparql_serv.setQuery(f"""
                            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                            PREFIX void: <http://rdfs.org/ns/void#>


                            DELETE WHERE {{
                                GRAPH <https://omnipot.acdh.oeaw.ac.at/provenance> {{
                                    <{base_uri}/entities#> void:{f}Partition ?o.
                                    ?o ?p ?s
                                    }}
                                    }}
                        """)
                        res4 = sparql_serv.query().convert()
                    sparql_serv.setQuery(f"""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                        PREFIX void: <http://rdfs.org/ns/void#>


                        DELETE WHERE {{
                          GRAPH <https://omnipot.acdh.oeaw.ac.at/provenance> {{
                            <{base_uri}/entities#> ?p ?o.
                            
                        }}
                        }}
                    """)
                    res4 = sparql_serv.query()
            header = {'Content-Type': map_ct[options['format']][0]}
            res2 = requests.post(url, headers=header, data=fin.serialize(format=options['format']), auth=(username, password))
            sparql_serv.setQuery(sp_count)
            res_count_1 = sparql_serv.query().convert()
            count = int(res_count_1['results']['bindings'][0]['triples']['value'])
            if count > 0:
                self.stdout.write(self.style.NOTICE(f'Found {count} triples after update in store'))
            if res2.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Something went wrong when updating: {res2.text}'))
            else:
                self.stdout.write(self.style.SUCCESS('Updated the triplestore.'))
