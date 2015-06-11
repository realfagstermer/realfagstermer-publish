#!/bin/sh

# Genererates list of triples added and removed between two dates

# TODO: Accept cmd line args
DATE_FROM="2015-05-01"
DATE_UNTIL="2015-05-31"
BASENAME="realfagstermer"


function test_exit_status()
{
	if [ $1 != 0 ]; then
	    echo
	    echo -----------------------------------------------------------
	    echo ERROR:
	    echo $2
	    echo -----------------------------------------------------------
	    exit 1
	fi
}

cd realfagstermer
test_exit_status $?

# Note: Date is inclusive!
OLD_COMMIT=`git rev-list -1 --until="${DATE_FROM}" master`
git checkout $OLD_COMMIT
test_exit_status $? "Could not checkout. Is the repo clean?"
cp -f $BASENAME.ttl $BASENAME.old.ttl

NEW_COMMIT=`git rev-list -1 --until="${DATE_UNTIL}" master`
git checkout $NEW_COMMIT
test_exit_status $? "Could not checkout. Is the repo clean?"
cp -f $BASENAME.ttl $BASENAME.new.ttl
echo "Comparing $OLD_COMMIT .. $NEW_COMMIT"

git checkout master
test_exit_status $? "Could not checkout. Is the repo clean?"

rapper -i turtle -o ntriples $BASENAME.old.ttl >| $BASENAME.old.nt
rapper -i turtle -o ntriples $BASENAME.new.ttl >| $BASENAME.new.nt

diff --suppress-common-lines $BASENAME.old.nt $BASENAME.new.nt >| diff.tmp

# grep -v '<http://purl.org/dc/terms/modified>' | 
cat diff.tmp | grep '^>' | cut -c 3- | sort >| added.nt
cat diff.tmp | grep '^<' | cut -c 3- | sort >| removed.nt

# In cases where a line just moves to a new position, it might 
# be present in both 'added' and 'removed'. Let's make sure we
# have filtered those out.

echo "
added = set(open('added.nt').readlines())
removed = set(open('removed.nt').readlines())

added2 = added.difference(removed)
removed2 = removed.difference(added)

open('added.nt','w').writelines(added2)
open('removed.nt','w').writelines(removed2)
" | python
