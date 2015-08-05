TEST_FILES := $(wildcard test-*.sh)
TESTS := $(TEST_FILES:.sh=.test)

testall: $(TESTS)

%.test:
	bash $*.sh > $@ 2>&1

clean:
	rm -f *.test
