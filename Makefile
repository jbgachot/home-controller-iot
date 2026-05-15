.PHONY: help
help: # Show help for each of the targets.
	@printf "\033[1;32mUsage: make [options] [target] ...\n"
	@printf "\033[1;00mOptions:\n"
	@grep -E '^[a-zA-Z0-9 -]+:.*#' Makefile | while read -r l; do printf "  \033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

# Tools
MISE ?= mise
PDM ?= pdm
MPREMOTE ?= pdm run mpremote

MISE_EXISTS := $(shell command -v $(MISE) 2> /dev/null)
PDM_EXISTS := $(shell command -v $(PDM) 2> /dev/null)
MPREMOTE_EXISTS := $(shell command -v $(MPREMOTE) 2> /dev/null)

.PHONY: with-mise
with-mise:
ifndef MISE_EXISTS
	@curl https://mise.run | sh
endif

.PHONY: install
install: with-mise # Install all prerequisites.
	$(MISE) install
	$(PDM) install

.PHONY: with-deps
with-deps:
ifndef PDM_EXISTS
	make install
endif
ifndef MPREMOTE_EXISTS
	make install
endif

.PHONY: run
run: with-deps # Send project to the serial device and reset.
	$(MPREMOTE) \
		cp main.py : + \
		cp secrets.py : + \
		cp -r src/ : + \
		reset

.PHONY: reset
reset: with-deps # Hard reset the serial device
	$(MPREMOTE) reset

.PHONY: bootloader
bootloader: with-deps # Make the serial device enter in bootloader mode.
	$(MPREMOTE) bootloader

.PHONY: repl
repl: with-deps # Enter in the REPL of the serial device.
	$(MPREMOTE) repl

.PHONY: style
style: with-deps # Run linter and formater.
	$(PDM) run lint
	$(PDM) run format
