.PHONY: contracts check-contracts test-api test-ui test-e2e audit export-claims validate download-data reuse-data prep generate check-data up down notebook mcp
contracts check-contracts test-api test-ui test-e2e audit export-claims validate download-data reuse-data prep generate check-data up down notebook mcp:
	$(MAKE) -C .. $@ TEST_ARGS="$(TEST_ARGS)" UI_ARGS="$(UI_ARGS)" E2E_ARGS="$(E2E_ARGS)" TEAM="$(TEAM)" CLAIMS="$(CLAIMS)" URL="$(URL)"
