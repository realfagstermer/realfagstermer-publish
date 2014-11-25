# encoding=utf8
import datetime
import pytz   # timezone in Python 3
from dateutil.parser import parse
import logging
import logging.handlers
import os
import time
import sys
import requests
from rdflib.graph import Graph, ConjunctiveGraph, Dataset, Literal
from rdflib.namespace import Namespace, URIRef, OWL, RDF, DC, DCTERMS, FOAF, XSD, SKOS
from rdflib import BNode
import datetime
from serializer import OrderedXMLSerializer
from rdflib.plugins.serializers.turtle import RecursiveSerializer, TurtleSerializer

import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s %(levelname)s] %(message)s')

console_handler = logging.StreamHandler(stream=sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

warn_handler = logging.FileHandler('warnings.log')
warn_handler.setLevel(logging.WARNING)
warn_handler.setFormatter(formatter)
logger.addHandler(warn_handler)


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


def make():
    """
    Combine data from roald.rdf and mumapper.rdf, add some metadata and serialize
    """

    RDAC = Namespace('http://rdaregistry.info/Elements/c/')
    MADS = Namespace('http://www.loc.gov/mads/rdf/v1#')
    CC = Namespace('http://creativecommons.org/ns#')

    ds = Dataset()

    with open('roald.rdf.2', 'w') as outfile:
        with open('roald.rdf', 'r') as infile:
            for line in infile:
                outfile.write(line.replace('data.ub.uio.nu', 'data.ub.uio.no'))

    with open('mumapper.rdf.2', 'w') as outfile:
        with open('mumapper.rdf', 'r') as infile:
            for line in infile:
                outfile.write(line.replace('data.ub.uio.nu', 'data.ub.uio.no'))

    os.rename('roald.rdf.2', 'roald.rdf')
    os.rename('mumapper.rdf.2', 'mumapper.rdf')

    logger.info('Adding roald.rdf to dataset')
    roald = ds.graph(URIRef('file:///roald'))  # named graph
    roald.load('roald.rdf')

    logger.info('Adding mumapper.rdf to dataset')
    mumapper = ds.graph(URIRef('file:///mumapper'))  # named graph
    mumapper.load('mumapper.rdf')

    out = Graph()
    out.namespace_manager.bind('owl', OWL)
    out.namespace_manager.bind('skos', SKOS)
    out.namespace_manager.bind('dcterms', DCTERMS)
    out.namespace_manager.bind('foaf', FOAF)
    out.namespace_manager.bind('cc', CC)
    out.namespace_manager.bind('xsd', XSD)
    out.namespace_manager.bind('mads', MADS)

    vocabulary = URIRef('http://data.ub.uio.no/realfagstermer/')
    out.add((vocabulary, RDF.type, SKOS.ConceptScheme))

    # Add title, description and datestamp

    # http://dublincore.org/documents/dcmi-terms/#terms-title
    out.add((vocabulary, DCTERMS.title, Literal('Realfagstermer', lang='nb')))

    # http://dublincore.org/documents/dcmi-terms/#terms-description
    out.add((vocabulary, DCTERMS.description, Literal('Realfagstermer er et kontrollert, pre-koordinert emneordsvokabular som i hovedsak dekker naturvitenskap, matematikk og informatikk.', lang='nb')))
    out.add((vocabulary, DCTERMS.description, Literal('Realfagstermer is a controlled, pre-coordinated subject headings vocabulary covering mainly the natural sciences, mathematics and informatics.', lang='en')))

    # http://dublincore.org/documents/dcmi-terms/#terms-type
    out.add((vocabulary, DCTERMS.type, URIRef('http://purl.org/dc/dcmitype/Dataset')))

    # http://wiki.dublincore.org/index.php/NKOS_AP_Elements
    out.add((vocabulary, DCTERMS.type, URIRef('http://purl.org/nkos/nkostype/subject_heading_scheme')))
    now = datetime.datetime.now()
    out.add((vocabulary, DCTERMS.modified, Literal(now.strftime('%F'), datatype=XSD.date)))

    # Add creator
    UBO = BNode()
    out.add((UBO, OWL.sameAs, URIRef('http://viaf.org/viaf/155670338/')))
    out.add((UBO, OWL.sameAs, URIRef('http://www.wikidata.org/entity/Q3354774')))
    out.add((UBO, OWL.sameAs, URIRef('http://dbpedia.org/resource/University_Library_of_Oslo')))
    # x90065017
    out.add((UBO, RDF.type, FOAF.Organization))

    # out.add((UBO, RDF.type, RDAC.C10005)) # Corporate body
    # http://metadataregistry.org/uri/orgtype/n60  # ISIL organization type
    out.add((UBO, DCTERMS.title, Literal('Universitetsbiblioteket i Oslo', lang='nb')))
    out.add((UBO, DCTERMS.title, Literal('University Library of Oslo', lang='en')))

    # http://dublincore.org/documents/dcmi-terms/#terms-creator
    out.add((vocabulary, DCTERMS.creator, UBO))

    # Add license
    out.add((vocabulary, DCTERMS.license, URIRef('http://creativecommons.org/publicdomain/zero/1.0/')))
    out.add((vocabulary, CC.license, URIRef('http://creativecommons.org/publicdomain/zero/1.0/')))

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

    s = TurtleSerializer(out)
    s.topClasses = [SKOS.ConceptScheme, SKOS.Concept]  # These will appear first in the file
    s.serialize(open('realfagstermer.ttl', 'w'))
    logger.info('Wrote realfagstermer.ttl')


def run():

    roald = {
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
