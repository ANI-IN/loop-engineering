# DataPilot Makefile. Every target is a thin wrapper over `uv run ...` or `docker compose ...`, so
# the same commands work without make (docs/reference.md lists each one). On Windows, run make
# inside Ubuntu on WSL2. Targets take readable names, never numbers: make demo NAME=<slug>.

SHELL := /bin/bash
UV ?= uv
COMPOSE ?= docker compose
CHECK_STYLE_OPTS ?=
NAME ?=
PURPOSE ?=
STEP ?=
ARGS ?=
# The tests' own stack. Set with :=, not ?=, so an exported shell variable never points these
# targets at another project: TEST_STACK=datapilot in the environment would stop the class stack.
# make TEST_STACK=... on the command line still counts.
TEST_STACK := datapilot-tests
TEST_POSTGRES_PORT := 55432
# One run at a time on the tests' own database: parallel checkouts queue on this lock, and so
# does starting it, since a checkout elsewhere recreates the container from its own folder.
TEST_LOCK := /tmp/datapilot-tests-database.lock
VARIANT ?=
TREE ?=
PACK ?=
PLANTED ?=
ONCE ?=
# The variables a target reads count only when given on make's command line (make demo NAME=x).
# A shell may export any of them for its own reasons: WSL sets NAME to the computer's name in
# every shell. One that comes from the environment is emptied here and kept out of every recipe's
# environment, so no target acts on it. MAKEFLAGS is make's own command line, as a parent make
# passes it to a sub-make: a variable defined there counts as given on the command line.
COMMAND_LINE_ONLY := NAME PURPOSE STEP ARGS VARIANT TREE PACK PLANTED ONCE LEVEL BY RUN REPO FORCE
$(foreach variable,$(COMMAND_LINE_ONLY),$(if $(filter command line,$(origin $(variable))),,$(eval unexport $(variable))$(eval override $(variable) :=)))

.PHONY: verify help setup up restart down ps logs migrate seed check-data spend test-stack test-stack-down live-smoke preflight hill-climbing-runner calibrate style-tile demos registries outline docs docs-check test test-integration test-console 	lint format import-lint lint-prose check-style check-style-strict check-short-forms check-names check 	demo reset reset-discarding-baseline archive archive-show safeguard-status safeguard-verify safeguard-activate autonomy open-code test-security 	check-assignment apply-solution verify-assignments diagrams check-pack ci-local check-images

help: ## List every target
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Install the pinned packages and create .env from .env.example if missing
	$(UV) sync --frozen
	@test -f .env || (cp .env.example .env && echo '+ created .env: add OPENAI_API_KEY and LANGSMITH_API_KEY')

up: ## Build and start postgres, api, worker, scheduler, hill-climbing runner, and console; wait until healthy
	@mkdir -p $(HOME)/.datapilot
	# Build first, then start: a combined "up --build" stalled in the image build under WSL.
	$(COMPOSE) build
	$(COMPOSE) up --detach --wait

restart: ## Recreate every service from the image already built, so a changed .env takes effect; wait until healthy (no image build)
	@mkdir -p $(HOME)/.datapilot
	$(COMPOSE) up --detach --wait --no-build --force-recreate

down: ## Stop every service (the database volume is kept)
	$(COMPOSE) down

ps: ## Show the services and their health
	$(COMPOSE) ps

logs: ## Follow the logs of every service; NAME=<service> for one
	$(COMPOSE) logs --follow $(NAME)

migrate: ## Apply the ops schema migrations against the Compose database
	$(UV) run datapilot migrate

spend: ## The build's model spend so far, by activity, against the budget in pack.yaml
	$(UV) run datapilot spend

style-tile: ## The console design style tile on http://localhost:8531 (specimen data, no database)
	cd platform/console && $(UV) run streamlit run design_app.py --server.port 8531

demos: ## List every demo with its readable name
	$(UV) run datapilot demos

registries: ## Validate the demo and planted-item registries
	$(UV) run datapilot check-registries

outline: ## Rebuild slides/outline.md from slides/source/ and check every slide rule
	$(UV) run python slides/source/build.py slides/outline.md

docs: ## Regenerate every generated page from its registry
	$(UV) run python platform/tools/generators/render.py

docs-check: ## Fail if any generated page is out of date (CI and the release gate)
	$(UV) run python platform/tools/generators/render.py --check

test: ## The zero-token suites (no model calls, no database)
	$(UV) run pytest -q -m "not integration and not live"

test-stack: ## The tests' own Postgres (Compose project datapilot-tests, port 55432), migrated and seeded
	flock $(TEST_LOCK) env POSTGRES_PORT=$(TEST_POSTGRES_PORT) $(COMPOSE) -p $(TEST_STACK) up --detach --wait postgres
	flock $(TEST_LOCK) env DATAPILOT_TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT) $(UV) run python platform/scripts/prepare_tests_database.py

test-stack-down: ## Stop the tests' own Postgres (its volume is kept)
	POSTGRES_PORT=$(TEST_POSTGRES_PORT) $(COMPOSE) -p $(TEST_STACK) down

test-integration: test-stack ## Zero-token tests on the tests' own database, never the live stack
	flock $(TEST_LOCK) env DATAPILOT_TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT) $(UV) run pytest -q -m integration

test-console: test-stack ## The console in a real browser on the tests' own database; rewrites platform/console/screenshots/
	flock $(TEST_LOCK) env DATAPILOT_TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT) DATAPILOT_CONSOLE_SCREENSHOTS=1 \
		$(UV) run pytest -q -m integration -k console_screens

lint: ## Ruff, the import contracts, the style check, the prose lint, and the naming check
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run lint-imports
	$(UV) run python platform/scripts/check_style.py $(CHECK_STYLE_OPTS)
	$(UV) run python platform/scripts/lint_prose.py
	@$(MAKE) --no-print-directory check-names

format: ## Rewrite files with ruff check --fix and ruff format
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

import-lint: ## The import contracts in pyproject.toml
	$(UV) run lint-imports

lint-prose: ## Banned words and emoji in the course pages
	$(UV) run python platform/scripts/lint_prose.py

check-style: ## Course style check (errors fail; CHECK_STYLE_OPTS=--strict for warnings)
	$(UV) run python platform/scripts/check_style.py $(CHECK_STYLE_OPTS)

check-style-strict: ## Style check where warnings fail too (the release gate)
	$(UV) run python platform/scripts/check_style.py --strict

guards: ## Repository guards: no core.worktree, no tracked .env; in the build also the git configuration allow-list, ANI-IN as the only author, no co-author lines
	$(UV) run python platform/scripts/check_repo_guards.py

ci-local: ## The continuous integration workflow's own steps in a clean clone, no secrets (Linux): make ci-local REPO=<release clone>
	@test -n "$(REPO)" || { echo "x name the release clone: make ci-local REPO=<folder>"; exit 2; }
	$(UV) run python platform/scripts/ci_local.py --repo "$(REPO)"

check-images: ## Published images: size, blank areas, clipped edges, alt text; ARGS=--rehearsal at the end of the rehearsal
	$(UV) run python platform/scripts/check_images.py $(ARGS)

check-short-forms: ## The naming rule on this branch's commit messages (the build only; read without a pipe)
	$(UV) run python platform/scripts/check_repo_guards.py --commit-messages

check-names: ## Naming rule: course pages, slides/outline.md, commit messages (CHECK_STYLE_OPTS=--strict)
	$(UV) run python platform/scripts/check_style.py --names-only $(CHECK_STYLE_OPTS)
	$(UV) run python platform/scripts/short_forms.py $(CHECK_STYLE_OPTS) slides/outline.md
	$(UV) run python platform/scripts/check_repo_guards.py --commit-messages

check: guards lint docs-check test ## Everything CI runs without a database

verify: ## The verification gate: every check, each result printed, fails if any one fails (before every commit and merge)
	UV=$(UV) bash platform/scripts/verify.sh

seed: ## Generate and load warehouse and warehouse_alt (deterministic; about a minute)
	$(UV) run datapilot seed

check-data: ## Row counts and content hash of both warehouses against the expected values
	$(UV) run datapilot check-data

check-pack: ## Check a domain pack, with both databases, before any model call: make check-pack PACK=<pack>
	@test -n "$(PACK)" || (echo 'name the pack: make check-pack PACK=<a folder under platform/packs>'; exit 2)
	$(UV) run python use-in-your-repo/check_pack.py $(PACK) --database

demo: ## Trigger a live demo through the api: make demo NAME=<demo slug> [PLANTED=1: its planted bugs on for its own runs only]
	$(UV) run datapilot demo $(NAME) $(if $(and $(filter command line,$(origin PLANTED)),$(filter 1,$(PLANTED))),--planted)

reset: ## Clear a section's live run state and release the kill switch: make reset NAME=<section>
	$(UV) run datapilot reset $(NAME)

reset-discarding-baseline: ## Full hill-climbing reset that also discards this session's baseline
	$(UV) run datapilot reset-discarding-baseline $(NAME)

archive: ## The reset archive's entries, newest first
	$(UV) run datapilot archive list

archive-show: ## One archived experiment: make archive-show NAME=<experiment id>
	$(UV) run datapilot archive show $(NAME)

safeguard-status: ## The version verified in rehearsal for the class-day safeguard
	$(UV) run datapilot safeguard status

safeguard-verify: ## In rehearsal: make safeguard-verify NAME=<version> RUN=<finale run id> BY="<your name>"
	$(UV) run datapilot safeguard verify "$(NAME)" --run "$(RUN)" --by "$(BY)"

safeguard-activate: ## In class, when the finale answer is wrong: make safeguard-activate BY="<your name>" [NAME=<version>: a verified version whatever its age]
	$(UV) run datapilot safeguard activate --by "$(BY)" $(if $(filter command line,$(origin NAME)),--version "$(NAME)")

autonomy: ## Set the system's autonomy level through the api: make autonomy LEVEL=unattended BY="<your name>"
	@test -n "$(LEVEL)" || (echo 'name the level: make autonomy LEVEL=report-only|assisted|unattended BY="<your name>"'; exit 2)
	@test -n "$(BY)" || (echo 'say who sets it: make autonomy LEVEL=$(LEVEL) BY="<your name>"'; exit 2)
	$(UV) run datapilot autonomy "$(LEVEL)" --by "$(BY)"

open-code: ## Open the code a section shows in class: make open-code NAME=<section slug>
	$(UV) run datapilot open-code $(NAME)

preflight: ## Services, the OpenAI key, the drift canary, then a new live session: make preflight PURPOSE=class
	@test -n "$(PURPOSE)" || (echo 'name the session: make preflight PURPOSE=class|rehearsal|thursday-review|development'; exit 2)
	$(UV) run datapilot preflight --purpose $(PURPOSE)

live-smoke: ## Five real calls across the system with tokens, cost, and trace links (development live checks)
	$(UV) run datapilot live-smoke

hill-climbing-runner: ## The runner outside Compose (make up runs it as a service); refuses while another runner serves
	$(UV) run datapilot hill-climbing-runner

calibrate: ## One live calibration step, raw results in .runs/calibration: make calibrate STEP=traps ARGS="--runs 3"
	@test -n "$(STEP)" || (echo 'name the step: canary, traps, experiment-starting, analyzer, experiment-candidate, stability-starting, stability-candidate, agents, confirm, analyzer-high, output-token-cap'; exit 2)
	$(UV) run datapilot calibrate $(STEP) $(ARGS)

test-security: test-stack ## The security suite, zero tokens (its second part runs on the tests' own database)
	flock $(TEST_LOCK) env DATAPILOT_TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT) $(UV) run pytest -q -k security

check-assignment: ## The live check of one assignment (model calls): make check-assignment NAME=<slug> [TREE=<copy>]
	$(UV) run python -m datapilot.assignments check $(NAME) $(if $(TREE),--tree $(TREE))

apply-solution: ## A scratch copy of the starter with one solution: make apply-solution NAME=<slug> VARIANT=<reference|alternative-one|alternative-two>
	$(UV) run python -m datapilot.assignments apply $(NAME) $(VARIANT)

verify-assignments: ## The build's live verification (model calls): each starter once, each solution twice, with captures [NAME=<slug>] [VARIANT=<variant>] [ONCE=1]
	DATAPILOT_SPEND_ACTIVITY="assignment verification" $(UV) run python -m datapilot.assignments verify $(if $(NAME),--only $(NAME)) $(foreach v,$(VARIANT),--variant $(v)) $(if $(filter 1,$(ONCE)),--once)

diagrams: ## Render the Excalidraw diagrams to SVG and PNG (authoring time; Playwright, dev group): ARGS=--build or --check
	$(UV) run python platform/tools/diagrams/export_diagrams.py $(ARGS)
