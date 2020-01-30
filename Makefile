DC := $(shell which docker-compose)
DOCKER := $(shell which docker)

# *IMPORTANT*
# Don't use this instance in a production setting. More info at:
# https://docs.djangoproject.com/en/dev/ref/django-admin/#runserver
SITE_URL ?= http://localhost:8000

USER_ID?=$(shell id -u)
GROUP_ID?=$(shell id -g)

.PHONY: build setup run clean test shell loaddb build-frontend build-frontend-w

help:
	@echo "Welcome to Pontoon!\n"
	@echo "The list of commands for local development:\n"
	@echo "  build            Builds the docker images for the docker-compose setup"
	@echo "  setup            Configures a local instance after a fresh build"
	@echo "  run              Runs the whole stack, served on http://localhost:8000/"
	@echo "  clean            Forces a rebuild of docker containers"
	@echo "  shell            Opens a Bash shell in a webpp docker container"
	@echo "  test             Runs the entire test suite (back and front)"
	@echo "  jest             Runs the new frontend's test suite (Translate.Next)"
	@echo "  pytest           Runs the backend's test suite (Python)"
	@echo "  flow             Runs the Flow type checker on the frontend code"
	@echo "  lint-frontend    Runs a code linter on the frontend code (Translate.Next)"
	@echo "  loaddb           Load a database dump into postgres, file name in DB_DUMP_FILE"
	@echo "  build-frontend   Builds the frontend static files"
	@echo "  build-frontend-w Watches the frontend static files and builds on change\n"


.docker-build:
	make build

build:
	cp ./docker/config/webapp.env.template ./docker/config/webapp.env
	sed -i -e 's/#SITE_URL#/$(subst /,\/,${SITE_URL})/g' ./docker/config/webapp.env

	"${DC}" build --build-arg USER_ID=$(USER_ID) --build-arg GROUP_ID=$(GROUP_ID) webapp

	touch .docker-build

setup: .docker-build
	"${DC}" run webapp //app/docker/set_up_webapp.sh

run: .docker-build
	"${DC}" run --rm --service-ports webapp

clean:
	rm .docker-build

test:
	"${DC}" run --rm webapp //app/docker/run_tests.sh

test-frontend: jest
jest:
	"${DC}" run --rm -w //app/frontend webapp yarn test

pytest:
	"${DC}" run --rm -w //app webapp pytest --cov-append --cov-report=term --cov=. $(opts)

flake8:
	"${DC}" run --rm -w //app webapp flake8

flow:
	"${DC}" run --rm -w //app/frontend -e SHELL=//bin/bash webapp yarn flow:dev

lint-frontend:
	"${DC}" run --rm -w //app/frontend webapp ./node_modules/.bin/eslint src/

shell:
	"${DC}" run --rm webapp //bin/bash

loaddb:
	# Stop connections to the database so we can drop it.
	-"${DC}" stop webapp
	# Make sure the postgresql container is running.
	-"${DC}" start postgresql
	-"${DC}" exec postgresql dropdb -U pontoon pontoon
	"${DC}" exec postgresql createdb -U pontoon pontoon
	# Note: docker-compose doesn't support the `-i` (--interactive) argument
	# that we need to send the dump file through STDIN. We thus are forced to
	# use docker here instead.
	"${DOCKER}" exec -i `"${DC}" ps -q postgresql` pg_restore -U pontoon -d pontoon -O < "${DB_DUMP_FILE}"

build-frontend:
	"${DC}" run --rm webapp npm run build

build-frontend-w:
	"${DC}" run --rm webapp npm run build-w
