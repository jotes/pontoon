#!/usr/bin/env bash -ex

function build_assets() {
  ./node_modules/.bin/webpack
  pushd frontend && npm run build && popd
  python manage.py collectstatic -v0 --noinput
}

case "$1" in
  pylama) echo "pylama"
      pylama pontoon
      pylama tests
  ;;

  eslint) echo "eslint"
      ./node_modules/.bin/eslint .
  ;;

  lint-heroku) echo "lint-heroku"
      cat app.json | python -m json.tool > /dev/null
  ;;

  test-backend) echo "test backend"
      build_assets

      py.test --cov-append --cov-report=term --cov=. -v --create-db --migrations
  ;;


  test-frontend) echo "test frontend"
      build_assets

      npm test
      pushd frontend && npm test && popd
  ;;


esac
