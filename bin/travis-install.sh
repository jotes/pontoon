#!/usr/bin/env bash -ex

function python_deps() {
  pip install -U --force pip
  pip install --require-hashes -r requirements.txt
  pip install --require-hashes -r requirements-test.txt
}


function build_frontend() {
  ./node_modules/.bin/webpack
  pushd frontend && npm run build && popd
  python manage.py collectstatic -v0 --noinput
}

function nodejs_deps() {
  source $HOME/.nvm/nvm.sh
  nvm install node
  nvm use node
  npm install --no-audit .
  pushd frontend && npm install --no-audit && popd
}

case "$1" in
  pylama) echo "pylama"
      pip install pylama
      pylama pontoon
      pylama tests
  ;;

  eslint) echo "eslint"
      nodejs_deps
      ./node_modules/.bin/eslint .
  ;;

  test-backend) echo "test backend"
       build_frontend
       python_deps
  ;;


  test-frontend) echo "test frontend"
      nodejs_deps
      build_frontend
  ;;


esac
