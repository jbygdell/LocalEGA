SHELL := /bin/bash

TARGET_PREFIX=egarchive/lega-

LEGA_GID=1000

# Must find better, but working so far
MAIN_REPO := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST))))/../..)

.PHONY: all erase purge base

all: base

base:
	cd $(MAIN_REPO) && \
	docker build -f Dockerfile \
	       --build-arg LEGA_GID=$(LEGA_GID) \
	       --cache-from $(TARGET_PREFIX)base:latest \
               --tag $(TARGET_PREFIX)$@:latest \
               .

define remove_dangling
    docker images $(1) -f "dangling=true" -q | uniq | while read n; do docker rmi -f $$n; done
endef

erase:
	@$(call remove_dangling,$(TARGET_PREFIX)base)

purge:
	@$(call remove_dangling,)
