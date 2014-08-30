Publishing script for Realfagstermer RDF/SKOS.

Run `make` to

1. Get RDF representation from Roald
2. Get mappings from µmapper
3. Combine and add metadata about the vocabulary itself (as a concept scheme)
4. Serialize as RDF/XML, NT, Turtle
5. Gzip?
5. TODO: Send update to triple store

Data model (work in progress)

Each subject is an instance of [skos:Concept](http://www.w3.org/2004/02/skos/core#Concept), and also one of [mads:Topic](http://www.loc.gov/mads/rdf/v1#Topic), [mads:Geographic](http://www.loc.gov/mads/rdf/v1#Geographic), [mads:Temporal](http://www.loc.gov/mads/rdf/v1#Temporal), [mads:GenreForm](http://www.loc.gov/mads/rdf/v1#GenreForm) or [mads:ComplexSubject](http://www.loc.gov/mads/rdf/v1#ComplexSubject), indicating the type of subject.


    @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
    @prefix xs: <http://www.w3.org/2001/XMLSchema#> .
    @prefix mads: <http://www.loc.gov/mads/rdf/v1#> .
    
    <http://data.ub.uio.no/realfagstermer/008317> a skos:Concept, mads:Topic
        skos:inScheme <http://data.ub.uio.no/realfagstermer/>
        skos:prefLabel "IR-spektroskopi"@nb  <!-- Burde det ikke vært "IR-spektroskopi"? -->
        skos:altLabel "Infrarød spektroskopi"@nb
        skos:narrower <http://data.ub.uio.no/realfagstermer/017797>
        skos:exactMatch <http://ntnu.no/ub/data/tekord#NTUB04964>,
            <http://dewey.info/class/535.842/e23/>
        dcterms:identifier "REAL008317"
        dcterms:created "2014-01-01"^^xs:date
        dcterms:modified "2014-08-30"^^xs:date
        dcterms:replaces <http://data.ub.uio.no/realfagstermer/000001>

Merging, deprecation, ...
* If concepts `<A>` and `<B>` are merged into concept `<C>`, we could 
** use `<A> dcterms:isReplacedBy <C> ; <B> dcterms:isReplacedBy <C>, <C> dcterms:replaces <A>, <B>`, and somehow mark `<A>` and `<B>` as deprecated or deleted. Not aware o a "standard" way to do that, so we might need to create our own `ub: <http://data.ub.uio.no/vocab#>` with `ub:deleted`?
** use MADS. Making `<A>` and `<B>` instances of [mads:DeprecatedAuthority](http://www.loc.gov/mads/rdf/v1#DeprecatedAuthority) and add `<A> mads:useInstead <C>, <B> mads:useInstead <C>`

