from rdflib.plugins.serializers.xmlwriter import XMLWriter

from rdflib.namespace import Namespace, RDF, RDFS, FOAF

from rdflib.term import URIRef, Literal, BNode
from rdflib.util import first, more_than
from rdflib.collection import Collection
from rdflib.serializer import Serializer
from rdflib.py3compat import b

from xml.sax.saxutils import quoteattr, escape
import xml.dom.minidom

from rdflib.plugins.serializers.xmlwriter import ESCAPE_ENTITIES

XMLLANG = "http://www.w3.org/XML/1998/namespacelang"
XMLBASE = "http://www.w3.org/XML/1998/namespacebase"
OWL_NS = Namespace('http://www.w3.org/2002/07/owl#')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')


# TODO:
def fix(val):
    "strip off _: from nodeIDs... as they are not valid NCNames"
    if val.startswith("_:"):
        return val[2:]
    else:
        return val


class OrderedXMLSerializer(Serializer):

    def __init__(self, store):
        super(OrderedXMLSerializer, self).__init__(store)
        self.forceRDFAbout = set()

    def serialize(self, stream, base=None, encoding=None, **args):
        self.__serialized = {}
        store = self.store
        self.base = base

        self.nm = nm = store.namespace_manager
        self.writer = writer = XMLWriter(stream, nm, encoding)
        namespaces = {}

        possible = set(store.predicates()).union(
            store.objects(None, RDF.type))

        for predicate in possible:
            prefix, namespace, local = nm.compute_qname(predicate)
            namespaces[prefix] = namespace

        namespaces["rdf"] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

        writer.push(RDF.RDF)

        if "xml_base" in args:
            writer.attribute(XMLBASE, args["xml_base"])

        writer.namespaces(namespaces.iteritems())

        # Ordered list of subjects at top level
        topSubjects = [
            {'name': SKOS.ConceptScheme, 'max_depth': 3},
            {'name': SKOS.Concept, 'max_depth': 1}
        ]
        for subject in topSubjects:
            self.max_depth = subject['max_depth']

            query = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?c
            WHERE
            {
                ?c a %s
            }
            ORDER BY ?c
            """ % (store.qname(subject['name']))
            # print query
            for row in store.query(query):
                # print row[0]
                self.subject(row[0], 1)
                # if (None, None, subject) in store:
                #     if (subject, None, subject) in store:
                #         print "ADD"
                #         self.subject(subject, 1)
                # else:
                #     print "ADD"
                #     self.subject(subject, 1)

        # write out anything that has not yet been reached
        # write out BNodes last (to ensure they can be inlined where possible)
        bnodes = set()

        for subject in store.subjects():
            if isinstance(subject, BNode):
                bnodes.add(subject)
                continue
            self.subject(subject, 1)

        # now serialize only those BNodes that have not been serialized yet
        for bnode in bnodes:
            if bnode not in self.__serialized:
                self.subject(subject, 1)

        writer.pop(RDF.RDF)
        stream.write(b("\n"))

        # Set to None so that the memory can get garbage collected.
        self.__serialized = None

    def getPreferredType(self, lst):
        # Prefer SKOS.Concept if available (over MADS.variant for instance)
        if SKOS.Concept in lst:
            return SKOS.Concept
        else:
            return first(lst)

    def subject(self, subject, depth=1):
        store = self.store
        writer = self.writer

        if subject in self.forceRDFAbout:
            writer.push(RDF.Description)
            writer.attribute(RDF.about, self.relativize(subject))
            writer.pop(RDF.Description)
            self.forceRDFAbout.remove(subject)

        elif subject not in self.__serialized:
            self.__serialized[subject] = 1
            type = self.getPreferredType(store.objects(subject, RDF.type))

            try:
                self.nm.qname(type)
            except:
                type = None

            element = type or RDF.Description
            writer.push(element)

            if isinstance(subject, BNode):
                def subj_as_obj_more_than(ceil):
                    return True
                    # more_than(store.triples((None, None, subject)), ceil)

                # here we only include BNode labels if they are referenced
                # more than once (this reduces the use of redundant BNode
                # identifiers)
                # if subj_as_obj_more_than(1):
                #     writer.attribute(RDF.nodeID, fix(subject))

            else:
                writer.attribute(RDF.about, self.relativize(subject))

            if (subject, None, None) in store:
                for predicate, object in store.predicate_objects(subject):
                    if not (predicate == RDF.type and object == type):
                        self.predicate(predicate, object, depth + 1)

            writer.pop(element)

        elif subject in self.forceRDFAbout:
            writer.push(RDF.Description)
            writer.attribute(RDF.about, self.relativize(subject))
            writer.pop(RDF.Description)
            self.forceRDFAbout.remove(subject)

    def predicate(self, predicate, object, depth=1):
        writer = self.writer
        store = self.store
        writer.push(predicate)

        if isinstance(object, Literal):
            if object.language:
                writer.attribute(XMLLANG, object.language)

            if (object.datatype == RDF.XMLLiteral and
                    isinstance(object.value, xml.dom.minidom.Document)):
                writer.attribute(RDF.parseType, "Literal")
                writer.text(u"")
                writer.stream.write(object)
            else:
                if object.datatype:
                    writer.attribute(RDF.datatype, object.datatype)
                writer.text(object)

        elif object in self.__serialized or not (object, None, None) in store:

            if isinstance(object, BNode):
                # if more_than(store.triples((None, None, object)), 0):
                #     writer.attribute(RDF.nodeID, fix(object))
                pass
            else:
                writer.attribute(RDF.resource, self.relativize(object))

        else:
            if first(store.objects(object, RDF.first)):     # may not have type
                                                            # RDF.List

                self.__serialized[object] = 1

                # Warn that any assertions on object other than
                # RDF.first and RDF.rest are ignored... including RDF.List
                import warnings
                warnings.warn(
                    "Assertions on %s other than RDF.first " % repr(object) +
                    "and RDF.rest are ignored ... including RDF.List",
                    UserWarning, stacklevel=2)
                writer.attribute(RDF.parseType, "Collection")

                col = Collection(store, object)

                for item in col:

                    if isinstance(item, URIRef):
                        self.forceRDFAbout.add(item)
                    self.subject(item)

                    if not isinstance(item, URIRef):
                        self.__serialized[item] = 1
            else:
                if first(store.triples_choices(
                    (object, RDF.type, [OWL_NS.Class, RDFS.Class]))) \
                        and isinstance(object, URIRef):
                    writer.attribute(RDF.resource, self.relativize(object))

                elif depth <= self.max_depth:
                    self.subject(object, depth + 1)

                elif isinstance(object, BNode):

                    if object not in self.__serialized \
                            and (object, None, None) in store \
                            and len(list(store.subjects(object=object))) == 1:
                        # inline blank nodes if they haven't been serialized yet
                        # and are only referenced once (regardless of depth)
                        self.subject(object, depth + 1)
                    # else:
                    #    writer.attribute(RDF.nodeID, fix(object))

                else:
                    writer.attribute(RDF.resource, self.relativize(object))

        writer.pop(predicate)
