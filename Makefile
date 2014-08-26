.PHONY: update_database clean

all: update_database clean
	echo "Done"

update_database: realfagstermer.rdf
	echo "TODO: Update database"

realfagstermer.rdf: tmp/mapper.rdf tmp/knut.rdf
	mkdir -p $(dir $@)
	./src/prepare.sh

tmp/mapper.rdf:
	mkdir -p $(dir $@)
	curl "https://mapper.biblionaut.net/relationships?targetVocabularies%5B%5D=3&label=&notation=&format=rdfxml" -o $@.download
	mv $@.download $@
	touch $@

tmp/knut.rdf:
	mkdir -p $(dir $@)
	curl "http://app.uio.no/ub/emnesok/data/ureal/rii/eksport/realfagstermer.xml" -o $@.download
	mv $@.download $@
	touch $@

clean:
	rm tmp/mapper.rdf
	rm tmp/knut.rdf
	rmdir tmp
