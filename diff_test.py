# encoding=utf-8
# Script that reads diffs produced by 'produce_diff.sh'
# and creates human readable HTML output
#
from __future__ import print_function
import rdflib
from rdflib.namespace import OWL, RDF, DC, DCTERMS, FOAF, XSD, URIRef, Namespace, SKOS
from rdflib.graph import Graph, ConjunctiveGraph, Dataset, Literal
from rdflib.compare import to_isomorphic, graph_diff
import logging
from jinja2 import Template
import codecs

MADS = Namespace('http://www.loc.gov/mads/rdf/v1#')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s %(levelname)s] %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logging.info('Loading removed.nt')
removed = Graph()
removed.load('realfagstermer/removed.nt', format='nt')

logging.info('Loading added.nt')
added = Graph()
added.load('realfagstermer/added.nt', format='nt')

logging.info('Loading realfagstermer.new.nt as <current>')
current = Graph()
current.load('realfagstermer/realfagstermer.new.nt', format='nt')
current.namespace_manager.bind('skos', SKOS)
current.namespace_manager.bind('mads', MADS)
current.namespace_manager.bind('dct', DCTERMS)


logging.info('Computing')

changes = []

removed_subjects = set(removed.subjects())
added_subjects = set(added.subjects())
subjects = added_subjects.union(removed_subjects)

# TODO: Sort subjects by dct:modified ?? Eller er det bedre å ha det alfabetisk som nå?

notInteresting = [DCTERMS.modified, RDF.type, SKOS.inScheme]


def get_label(concept, set1, set2, set3, lang='nb'):
    label = set1.preferredLabel(concept, lang=lang)
    if len(label) == 0:
        label = set2.preferredLabel(concept, lang=lang)
    if len(label) == 0:
        label = set3.preferredLabel(concept, lang=lang)
    if len(label) == 0:
        return ''
    else:
        return label[0][1]


def get_props(triples):
    o = {}
    for triple in triples:
        prop = current.namespace_manager.qname(triple[1])
        if isinstance(triple[2], Literal) and triple[2].language:
            prop = u'{}@{}'.format(prop, triple[2].language)
        if prop not in o:
            o[prop] = []
        o[prop].append(triple[2])
    return o


# Group subjects by new/deleted/changed
changes = {'new': [], 'deleted': [], 'changed': []}
for s in subjects:

    cat = 'changed'

    # Assume deleted if rdf:type skos:Concept was removed
    if len(set(removed.triples((s, RDF.type, SKOS.Concept)))) != 0:
        cat = 'deleted'

    # Assume added if rdf:type skos:Concept was added
    elif len(set(added.triples((s, RDF.type, SKOS.Concept)))) != 0:
        cat = 'new'

    elif len(set(current.triples((s, RDF.type, SKOS.Concept)))) == 0:
        # Skip concept schemes etc.
        continue

    label = get_label(s, added, removed, current)

    pa = get_props(added.triples((s, None, None)))
    pr = get_props(removed.triples((s, None, None)))
    props = {}
    for x, y in pa.items():
        if x in pr:
            props[x] = (pr[x], y)  # (old, new)
        else:
            props[x] = (None, y)  # (old, new)
    for x, y in pr.items():
        if x not in pa:
            props[x] = (y, None)  # (old, new)

    changes[cat].append({
        'uri': s,
        'prefLabel': label,
        'props': props
    })

for cat in ['new', 'deleted', 'changed']:

    # Alternatively we could sort by date, but currently
    # we don't have any dates for the deprecated subjects
    changes[cat] = sorted(changes[cat],
                          key=lambda x: x['prefLabel'])


prop_labels = {
    'skos:prefLabel@nb': 'Foretrukket term (nb)',
    'skos:prefLabel@nn': 'Foretrukket term (nn)',
    'skos:prefLabel@en': 'Foretrukket term (en)',
    'skos:prefLabel@la': 'Foretrukket term (la)',
    'skos:altLabel': 'Akronymer',
    'skos:altLabel@nb': 'Alternative termer (nb)',
    'skos:altLabel@nn': 'Alternative termer (nn)',
    'skos:altLabel@en': 'Alternative termer (en)',
    'skos:related': 'Relaterte begreper',
    'skos:definition@nb': 'Definisjon',
}


def prop_list(props):
    def tv(x):
        if isinstance(x, URIRef):
            return u'<a href="{}">{}</a>'.format(x, get_label(x, current, added, removed))
        else:
            return u'"{}"'.format(x.value)
    return map(tv, props)


def friendly_prop_name(value):
    return prop_labels.get(value, value)


def format_change(prop, value):
    old, new = value

    if old is None:
        return {'name': friendly_prop_name(prop), 'new_values': prop_list(new)}
    elif new is None:
        return {'name': friendly_prop_name(prop), 'old_values': prop_list(old)}
    else:
        return {'name': friendly_prop_name(prop), 'old_values': prop_list(old), 'new_values': prop_list(new)}


formatted = {}

for k, items in changes.items():
    formatted[k] = []
    for c in items:
        out = {'uri': c['uri'], 'label': c['prefLabel'], 'props': []}
        for prop, val in c['props'].items():
            if prop in ['rdf:type', 'skos:broader', 'skos:narrower', 'skos:inScheme', 'dct:created', 'dct:modified', 'dct:identifier']:
                continue

            out['props'].append(format_change(prop, val))

        if len(out['props']) != 0:
            formatted[k].append(out)

template = Template(u"""---
layout: default
title: Endringer
---

# Endringer : januar 2015

<div class="changelist">

{% macro ctable(items) -%}
    <table>
    {% for item in items %}

        <tr>
            <td colspan=2>
                <a class="header" href="{{ item.uri }}">{{ item.label }}</a>
            </td>
        </tr>
        {% for prop in item.props %}
        <tr>
            <th>
                {{ prop.name }}:
            </th>
            <td>
                {% if prop.old_values %}
                    <span>
                        {% for val in prop.old_values %}
                        <span class="removed">{{ val }}</span>
                        {% endfor %}
                    </span>
                {% endif %}
                {% if prop.old_values and prop.new_values %}
                <!-- → -->
                {% endif %}
                {% if prop.new_values %}
                    <span>
                        {% for val in prop.new_values %}
                        <span class="added">{{ val }}</span>
                        {% endfor %}
                    </span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    {% endfor %}
    </table>
{%- endmacro %}


<h2>Nye emneord</h2>

    <ul>
    {% for item in items.new %}

        <li>
            <a href="{{ item.uri }}">{{ item.label }}</a></h3>
        </li>
    {% endfor %}
    </ul>

<h2>Slettede emneord</h2>

    <ul>
    {% for item in items.deleted %}

        <li>
            <a href="{{ item.uri }}">{{ item.label }}</a></h3>
        </li>
    {% endfor %}
    </ul>

<h2>Endrede emneord</h2>

{{ ctable(items.changed) }}

</div>
""", trim_blocks=True, lstrip_blocks=True)

template.environment.trim_blocks = True
template.environment.lstrip_blocks = True

with codecs.open('./realfagstermer.github.io/changes/2015-05.md', 'w', 'utf-8') as f:
    f.write(template.render(items=formatted))
