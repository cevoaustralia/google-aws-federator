.PHONY: distclean

.DEFAULT: usage

usage:
	@echo "Make targets:"
	@echo "  distclean: clean out distribution package files"

distclean:
	rm -rf dist build *.egg-info
