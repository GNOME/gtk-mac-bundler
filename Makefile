PACKAGE = ige-mac-bundler
VERSION = 0.5.4
OLD_VERSION = 0.5.4

bindir=$(HOME)/.local/bin

all:
	@echo 'Run "make install" to install.'

install:
	@mkdir -p $(bindir)
	@sed "s,@PATH@,`pwd`,g" < ige-mac-bundler.in > $(bindir)/ige-mac-bundler
	@chmod a+x $(bindir)/ige-mac-bundler

distdir = $(PACKAGE)-$(VERSION)
dist:
	if test -f Changelog; then \
		mv Changelog Changelog.old; \
	fi
	echo -e "Changes in version ${VERSION}:\n" > Changelog
	git log --format=" - %s (%aN)" --no-merges bundler-${OLD_VERSION}...HEAD >> Changelog
	echo "" >> Changelog
	cat Changelog.old >> Changelog
	rm Changelog.old
	-rm -rf $(distdir)
	mkdir $(distdir)
	cp -p README COPYING NEWS Changelog Makefile ige-mac-bundler.in $(distdir)/
	mkdir $(distdir)/ui
	cp -p ui/* $(distdir)/ui/
	mkdir $(distdir)/bundler
	cp -p bundler/*.py $(distdir)/bundler/
	cp -p bundler/*.sh $(distdir)/bundler/
	mkdir $(distdir)/examples
	cp -p examples/* $(distdir)/examples/
	chmod -R a+r $(distdir)
	tar czf $(distdir).tar.gz $(distdir)
	rm -rf $(distdir)

.PHONY: all install
