# Every target runs inside Docker. Without `make` (e.g. Windows PowerShell),
# copy the `docker compose ...` command shown under a target.

export HOST_UID := $(shell id -u 2>/dev/null || echo 1000)
export HOST_GID := $(shell id -g 2>/dev/null || echo 1000)

RUN  := docker compose run --rm app
REPS ?= 5

.PHONY: help build data test core experiments lab shell check

help:
	@echo "make build                                   build the Docker image"
	@echo "make data                                    download the Spotify dataset into data/"
	@echo "make test                                    run all tests"
	@echo "make core MEMBER=you MACHINE=id              run the provided CORE suite"
	@echo "make experiments MEMBER=you MACHINE=id [ONLY=name] [REPS=n]"
	@echo "make lab                                     JupyterLab at http://127.0.0.1:8888"
	@echo "make shell                                   bash inside the container"
	@echo "make check                                   tests + submission checks (what graders run)"

build:
	docker compose build app

data:
	$(RUN) python -m loaders.download

test:
	$(RUN) python -m pytest

core: _need-ids
	$(RUN) python -m bench.core_suite --member $(MEMBER) --machine-id $(MACHINE) --reps $(REPS)

experiments: _need-ids
	$(RUN) python -m bench.experiments --member $(MEMBER) --machine-id $(MACHINE) --reps $(REPS) $(if $(ONLY),--only $(ONLY))

lab:
	docker compose up lab

shell:
	$(RUN) bash

check:
	$(RUN) python -m pytest
	$(RUN) python scripts/check_submission.py

.PHONY: _need-ids
_need-ids:
	@test -n "$(MEMBER)" -a -n "$(MACHINE)" || (echo "usage: make $(MAKECMDGOALS) MEMBER=yourname MACHINE=machine_id"; exit 2)
