# encoding=utf8
from __future__ import absolute_import
import datetime
import pytz   # timezone in Python 3
from dateutil.parser import parse
import logging
import logging.handlers
import os
import time
import sys
import json
import re
import requests
from configparser import ConfigParser
from rdflib.graph import Graph, ConjunctiveGraph, Dataset, Literal
from rdflib.namespace import Namespace, URIRef, OWL, RDF, DC, DCTERMS, FOAF, XSD, SKOS, RDFS
from rdflib import BNode
from rdflib.plugins.serializers.turtle import RecursiveSerializer, TurtleSerializer

from .serializer import OrderedXMLSerializer
from skosify import Skosify

import logging


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s %(levelname)s] %(message)s')

console_handler = logging.StreamHandler(stream=sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

config = ConfigParser()
config.read('{}/config.ini'.format(os.path.dirname(os.path.dirname(__file__))))
try:
    if len(config['papertrail']['host']) > 1 and len(config['papertrail']['port']) > 1:
        papertrail = logging.handlers.SysLogHandler(address=(config['papertrail']['host'], config['papertrail']['port']))
        f2 = logging.Formatter('%(asctime)s realfagstermer-publish %(levelname)s %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
        papertrail.setFormatter(f2)
        papertrail.setLevel(logging.INFO)
        logger.addHandler(papertrail)
except:
    pass

warn_handler = logging.FileHandler('warnings.log')
warn_handler.setLevel(logging.WARNING)
warn_handler.setFormatter(formatter)
logger.addHandler(warn_handler)


def stats(g):

    facets = {
        'Topic': {
            'concepts': 0,
            'terms': 0,
            'prefLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0},
            'altLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0}
        },
        'Temporal': {
            'concepts': 0,
            'terms': 0,
            'prefLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0},
            'altLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0}
        },
        'Geographic': {
            'concepts': 0,
            'terms': 0,
            'prefLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0},
            'altLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0}
        },
        'GenreForm': {
            'concepts': 0,
            'terms': 0,
            'prefLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0},
            'altLabels': {'nb': 0, 'nn': 0, 'en': 0, 'la': 0}
        },
        'ComplexSubject': {
            'concepts': 0,
            'terms': 0,
            'prefLabels': {}
        }
    }

    features = {
        'definition': 0,
        'editorialNote': 0,
        'related': 0,
        'exactMatch': 0,
        'closeMatch': 0,
        'relatedMatch': 0,
        'broadMatch': 0,
        'narrowMatch': 0,
    }

    mappingUris = {
        'agrovoc': 'http://aims.fao.org/aos/agrovoc/',
        'ddc': 'http://dewey.info/',
        'tekord': 'http://ntnu.no/ub/data/tekord'
    }

    mappings = {
        'agrovoc': 0,
        'ddc': 0,
        'tekord': 0
    }

    for x in g.triples_choices((None, [SKOS.exactMatch, SKOS.closeMatch, SKOS.relatedMatch, SKOS.broadMatch, SKOS.narrowMatch], None)):
        if type(x[2]) == URIRef:
            uri = str(x[2])
            for k, v in mappingUris.items():
                if uri.startswith(v):
                    mappings[k] += 1

    for featureName in features.keys():

        features[featureName] = int(g.query(u"""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX mads: <http://www.loc.gov/mads/rdf/v1#>
        SELECT (COUNT(DISTINCT ?o) AS ?c)
        WHERE {
          ?s skos:%s ?o
        }""" % featureName).bindings[0].values()[0].value)

    terms = {}
    for triple in g.triples_choices((None, [SKOS.prefLabel, SKOS.altLabel], None)):
        lang = triple[2].language
        if lang not in terms:
            terms[lang] = 0
        terms[lang] += 1

    terms['_sum'] = sum([v for x, v in terms.items()])

    sumConcepts = 0
    sumConceptsWithStrings = 0

    for facetName, facet in facets.items():

        facets[facetName]['concepts'] = int(g.query(u"""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX mads: <http://www.loc.gov/mads/rdf/v1#>
        SELECT (COUNT(DISTINCT ?s) AS ?c)
        WHERE {
          ?s a mads:%s .
        }""" % (facetName)).bindings[0].values()[0].value)

        sumConceptsWithStrings += facets[facetName]['concepts']

        if facetName is not 'ComplexSubject':
            sumConcepts += facets[facetName]['concepts']

        facets[facetName]['terms'] = 0

        for langName in facet['prefLabels'].keys():

            facets[facetName]['prefLabels'][langName] = int(g.query(u"""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX mads: <http://www.loc.gov/mads/rdf/v1#>
            SELECT (COUNT(DISTINCT ?o) AS ?c)
            WHERE {
              ?s a mads:%s .
              ?s skos:prefLabel ?o .
              FILTER(langMatches(lang(?o), "%s"))
            }""" % (facetName, langName)).bindings[0].values()[0].value)

            facets[facetName]['altLabels'][langName] = int(g.query(u"""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX mads: <http://www.loc.gov/mads/rdf/v1#>
            SELECT (COUNT(DISTINCT ?o) AS ?c)
            WHERE {
              ?s a mads:%s .
              ?s skos:altLabel ?o .
              FILTER(langMatches(lang(?o), "%s"))
            }""" % (facetName, langName)).bindings[0].values()[0].value)

            facets[facetName]['terms'] += facets[facetName]['prefLabels'][langName] + facets[facetName]['altLabels'][langName]

    return {
        'concepts': sumConceptsWithStrings,
        'conceptsWithoutStrings': sumConcepts,
        'terms': terms,
        'facets': facets,
        'features': features,
        'mappings': mappings
    }


def fetch(url, filename):
    """
    Download a file from an URL
    """
    with open(filename, 'wb') as handle:
        response = requests.get(url, stream=True)

        if not response.ok:
            logger.error('Download failed')
            return False

        for block in response.iter_content(1024):
            if not block:
                break

            handle.write(block)

    logger.info(' -> Rewriting URIs')
    q = re.compile(r'http://data.ub.uio.no/realfagstermer/([0-9]+)')
    with open(filename, 'r') as infile:
        with open(filename + '.tmp', 'w') as outfile:
            outfile.write(q.sub('http://data.ub.uio.no/realfagstermer/c\\1', infile.read()))
    os.unlink(filename)
    os.rename(filename + '.tmp', filename)

    return True


def check_modification_dates(record):
    """
    Check modification date for remote and local file
    """

    head = requests.head(record['remote_url'])
    record['remote_datemod'] = parse(head.headers['last-modified'])
    if os.path.isfile(record['local_file']):
        record['local_datemod'] = datetime.datetime.fromtimestamp(os.path.getmtime(record['local_file']))
    else:
        # use some date in the past
        record['local_datemod'] = x = datetime.datetime(year=2014, month=1, day=1)
    record['local_datemod'] = record['local_datemod'].replace(tzinfo=pytz.utc)

    logger.info('   Remote file modified: %s' % (record['remote_datemod'].isoformat()))
    logger.info('    Local file modified: %s' % (record['local_datemod'].isoformat()))

    if record['remote_datemod'] < record['local_datemod']:
        logger.info(' -> Local data are up-to-date.')
        record['modified'] = False
        return record

    logger.info(' -> Fetching updated data...')
    fetch(record['remote_url'], record['local_file'])
    record['modified'] = True
    return record


def load_inputfiles():

    ds = Dataset()

    logger.info('Adding roald.rdf to dataset')
    roald = ds.graph(URIRef('file:///roald'))  # named graph
    roald.load('roald.rdf')

    logger.info('Adding mumapper.rdf to dataset')
    mumapper = ds.graph(URIRef('file:///mumapper'))  # named graph
    mumapper.load('mumapper.rdf')

    return ds


def process(ds):

    RDAC = Namespace('http://rdaregistry.info/Elements/c/')
    MADS = Namespace('http://www.loc.gov/mads/rdf/v1#')
    CC = Namespace('http://creativecommons.org/ns#')

    out = Graph()
    out.parse('vocabulary.ttl', format='turtle')
    # out.namespace_manager.bind('owl', OWL)
    # out.namespace_manager.bind('skos', SKOS)
    # out.namespace_manager.bind('dcterms', DCTERMS)
    # out.namespace_manager.bind('foaf', FOAF)
    # out.namespace_manager.bind('cc', CC)
    # out.namespace_manager.bind('xsd', XSD)
    # out.namespace_manager.bind('mads', MADS)

    res = ds.query("""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    CONSTRUCT {
        ?concept ?rel ?value .
    }
    WHERE
    {
        {
            GRAPH <file:///roald> {
                ?concept a skos:Concept ;
                         ?rel ?value .
            }
        } UNION {
            GRAPH <file:///mumapper> {
                ?concept (skos:exactMatch | skos:closeMatch | skos:broadMatch | skos:narrowMatch | skos:relatedMatch) ?value ;
                    ?rel ?value .
            }
        }
    }
    """)

    # Add existing triples
    for q in res:
        out.add(q)

    return out


def skosify_process(voc):

    logging.info("Performing inferences")

    skosify = Skosify()

    skosify.infer_classes(voc)
    skosify.infer_properties(voc)

    # logging.info("Setting up namespaces")
    # skosify.setup_namespaces(voc, namespaces)

    # logging.info("Phase 4: Transforming concepts, literals and relations")

    # special transforms for labels: whitespace, prefLabel vs altLabel
    # skosify.transform_labels(voc, options.default_language)

    # special transforms for collections + aggregate and deprecated concepts
    # skosify.transform_collections(voc)

    # find concept schema and update date modified
    cs = skosify.get_concept_scheme(voc)
    skosify.initialize_concept_scheme(voc, cs,
                                      label=False,
                                      language='nb',
                                      set_modified=True)

    # skosify.transform_aggregate_concepts(voc, cs, relationmap, options.aggregates)
    # skosify.transform_deprecated_concepts(voc, cs)

    # logging.info("Phase 5: Performing SKOS enrichments")

    # Enrichments: broader <-> narrower, related <-> related
    # skosify.enrich_relations(voc, options.enrich_mappings,
    #                  options.narrower, options.transitive)

    # logging.info("Phase 6: Cleaning up")

    # Clean up unused/unnecessary class/property definitions and unreachable
    # triples
    # if options.cleanup_properties:
    #     skosify.cleanup_properties(voc)
    # if options.cleanup_classes:
    #     skosify.cleanup_classes(voc)
    # if options.cleanup_unreachable:
    #     skosify.cleanup_unreachable(voc)

    # logging.info("Phase 7: Setting up concept schemes and top concepts")

    # setup inScheme and hasTopConcept
    # skosify.setup_concept_scheme(voc, cs)
    # skosify.setup_top_concepts(voc, options.mark_top_concepts)

    logging.info("Phase 8: Checking concept hierarchy")

    # check hierarchy for cycles
    skosify.check_hierarchy(voc, break_cycles=True, keep_related=False,
                            mark_top_concepts=False, eliminate_redundancy=True)

    # logging.info("Phase 9: Checking labels")

    # check for duplicate labels
    # skosify.check_labels(voc, options.preflabel_policy)


def make():
    """
    Combine data from roald.rdf and mumapper.rdf, add some metadata,
    do some skosify checks and serialize.
    """

    starttime = time.time()

    ds = load_inputfiles()
    inputtime = time.time()

    out = process(ds)
    skosify_process(out)
    processtime = time.time()

    # Add skos:inScheme to all concepts
    # for q in roald.triples((None, RDF.type, SKOS.Concept)):
    #     out.add((q[0], SKOS.inScheme, vocabulary))

    # xml:
    #
    #  <rdf:Description rdf:about="http://folk.uio.no/knuthe/emne/data/xml/#REAL030177">
    #    <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
    #    <skos:prefLabel xml:lang="nb">Matematiske tabeller</skos:prefLabel>
    #  </rdf:Description>
    #

    # pretty-xml:
    #
    #  <skos:Concept rdf:about="http://folk.uio.no/knuthe/emne/data/xml/#REAL030177">
    #    <skos:prefLabel xml:lang="nb">Matematiske tabeller</skos:prefLabel>
    #  </skos:Concept>
    #

    logger.info('Serializing...')

    s = OrderedXMLSerializer(out)
    s.serialize(open('realfagstermer.rdf.xml', 'w'), max_depth=1)
    logger.info('Wrote realfagstermer.rdf.xml')

    out.serialize(open('realfagstermer.nt', 'w'), format='nt')
    logger.info('Wrote realfagstermer.nt')

    SD = Namespace('http://www.w3.org/ns/sparql-service-description#')

    s = TurtleSerializer(out)

    # These will appear first in the file and be ordered by URI
    s.topClasses = [SKOS.ConceptScheme,
                    FOAF.Organization,
                    SD.Service,
                    SD.Dataset,
                    SD.Graph,
                    SD.NamedGraph,
                    SKOS.Concept]

    fobj = open('realfagstermer.ttl', 'w')
    fobj.write('@base <http://data.ub.uio.no/> .\n')
    s.serialize(fobj, base='http://data.ub.uio.no/')
    logger.info('Wrote realfagstermer.ttl')

    now = int(time.time())
    # now = datetime.datetime.now()
    s = json.load(open('stats.json', 'r'))
    current = stats(out)
    current['ts'] = now
    s.append(current)

    json.dump(current, open('stats_current.json', 'w'), indent=2, sort_keys=True)
    json.dump(s, open('stats.json', 'w'), indent=2)

    endtime = time.time()

    logging.info("Reading input files took  %d seconds",
                 (inputtime - starttime))
    logging.info("Processing took          %d seconds",
                 (processtime - inputtime))
    logging.info("Writing output file took %d seconds",
                 (endtime - processtime))
    logging.info("Total time taken:        %d seconds", (endtime - starttime))


def run():

    roald = {  # 'http://app.uio.no/ub/emnesok/data/test/ureal/rii/eksport/realfagstermer.xml'
        'remote_url': 'http://app.uio.no/ub/emnesok/data/ureal/rii/eksport/realfagstermer.xml',
        'local_file': 'roald.rdf'
    }
    mumapper = {
        'remote_url': 'http://mapper.biblionaut.net/export.rdf',
        'local_file': 'mumapper.rdf'
    }

    logger.info('Checking Roald...')
    roald = check_modification_dates(roald)

    logger.info(u'Checking µmapper...')
    mumapper = check_modification_dates(mumapper)

    if not roald['modified'] and not mumapper['modified']:
        logger.info('No changes. Exiting.')
        sys.exit(1)  # tells prepare.sh that there's no need to continue

    make()


if __name__ == '__main__':
    run()
