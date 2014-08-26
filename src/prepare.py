from rdflib.graph import Graph, ConjunctiveGraph, Dataset, Literal
from rdflib.namespace import OWL, RDF, DC, DCTERMS, FOAF, XSD, URIRef, Namespace
from rdflib import BNode
import datetime
from serializer import OrderedXMLSerializer

SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
RDAC = Namespace('http://rdaregistry.info/Elements/c/')
MADS = Namespace('http://www.loc.gov/mads/rdf/v1#')
CC = Namespace('http://creativecommons.org/ns#')

ds = Dataset()

# Fra
# app.uio.no/ub/emnesok/data/ureal/rii/eksport/realfagstermer.xml

print 'Adding knut.rdf to dataset'
g1 = ds.graph(URIRef('file:///realfagstermer'))
g1.load('tmp/knut.rdf')

print 'Adding mapper.rdf to dataset'
g2 = ds.graph(URIRef('file:///mapper'))
g2.load('tmp/mapper.rdf')

print 'Preparing realfagstermer.rdf'
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
        GRAPH <file:///realfagstermer> {
            ?concept a skos:Concept ;
                     ?rel ?value .
        }
    } UNION {
        GRAPH <file:///mapper> {
            ?concept (skos:exactMatch | skos:broadMatch) ?value ;
                ?rel ?value .
        }
    }
}
""")

for q in res:
    out.add(q)

for q in g1.triples((None, RDF.type, SKOS.Concept)):
    out.add((q[0], SKOS.inScheme, vocabulary))

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

s = OrderedXMLSerializer(out)
s.serialize(open('realfagstermer.rdf', 'w'), max_depth=1)

out.serialize(open('realfagstermer.nt', 'w'), format='nt')
out.serialize(open('realfagstermer.ttl', 'w'), format='turtle')
