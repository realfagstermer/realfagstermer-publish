.PHONY: realfagstermer.ttl

all: realfagstermer.ttl

realfagstermer.ttl:
	./src/prepare.sh

clean:
	rm -f mumapper.rdf
	rm -f roald.rdf
	rm -f realfagstermer.ttl
	rm -f realfagstermer.nt
	rm -f realfagstermer.rdf
