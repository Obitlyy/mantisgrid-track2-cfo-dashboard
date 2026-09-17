SHELL := /bin/sh
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DOCKER ?= $(shell command -v docker 2>/dev/null || echo /Applications/Docker.app/Contents/Resources/bin/docker)
UV ?= uv
PYRUN = $(UV) run --isolated --no-project --python 3.12 --with-requirements $(ROOT)/track-2/requirements.dev.lock.txt
override TEAM := $(value TEAM)
override REQUEST := $(value REQUEST)
override CLAIMS := $(value CLAIMS)
override URL := $(value URL)
export TEAM REQUEST CLAIMS URL
.PHONY: contracts check-contracts test-api test-ui test-e2e audit export-claims validate download-data reuse-data prep generate check-data up down notebook mcp

contracts:
	cd $(ROOT) && PYTHONPATH=$(ROOT)/track-2 $(PYRUN) python $(ROOT)/track-2/scripts/export_contracts.py --output $(ROOT)/track-2/contracts
	npm --prefix $(ROOT)/track-2/dashboard run contracts
check-contracts:
	cd $(ROOT) && PYTHONPATH=$(ROOT)/track-2 $(PYRUN) python $(ROOT)/track-2/scripts/check_contracts.py
test-api:
	cd $(ROOT) && PYTHONPATH=$(ROOT)/track-2:$(ROOT)/track-2/tests $(PYRUN) python -m pytest $(or $(TEST_ARGS),track-2/tests -q)
test-ui:
	npm --prefix $(ROOT)/track-2/dashboard run typecheck
	npm --prefix $(ROOT)/track-2/dashboard test -- $(UI_ARGS)
test-e2e:
	npm --prefix $(ROOT)/track-2/dashboard run test:e2e -- $(E2E_ARGS)
download-data:
	$(DOCKER) compose -f "$(ROOT)/docker-compose.yml" run --rm prep python scripts/download_data.py --destination /app/data/raw
reuse-data:
	$(PYRUN) python $(ROOT)/track-2/scripts/reuse_data.py --source $(ROOT)/track-2/data --destination $(ROOT)/data
prep:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml run --rm prep
generate:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml run --rm generate
check-data:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml run --rm prep python scripts/checksum_data.py --data /app/data --expect /app/official-checksums.txt
up:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml up --build
down:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml down
notebook:
	$(DOCKER) compose -f $(ROOT)/docker-compose.yml --profile notebook up notebook
mcp:
	cd $(ROOT)/track-2 && MGAI_DATA_DIR=$(ROOT)/data $(PYRUN) python -m mcp_layer.server
audit:
	cd "$(ROOT)" && PYTHONPATH="$(ROOT)/track-2" $(PYRUN) python -m decision.cli audit --data-dir "$(ROOT)/data" --output-dir "$(ROOT)/out"
export-claims:
	@set -- --team "$$TEAM" --output "$${CLAIMS:-$(ROOT)/claims.json}"; if [ -n "$$REQUEST" ]; then set -- "$$@" --request "$$REQUEST"; fi; cd "$(ROOT)" && PYTHONPATH="$(ROOT)/track-2" $(PYRUN) python -m decision.cli export-claims "$$@"
validate:
	@set -- --claims "$${CLAIMS:-$(ROOT)/claims.json}"; if [ -n "$$URL" ]; then set -- "$$@" --dashboard-url "$$URL"; fi; cd "$(ROOT)" && PYTHONPATH="$(ROOT)/track-2" $(PYRUN) python -m decision.cli validate "$$@"
