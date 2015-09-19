#!/bin/bash

set -x -e

export PROJECT_DIR="/vagrant/"
export VIRTUALENV_DIR="/home/vagrant/virtualenvs/pontoon"
# Generate random secret keys
export SECRET_KEY=$(head -c 20 /dev/urandom | xxd -ps)
export HMAC_KEY=$(head -c 20 /dev/urandom | xxd -ps)
export DB_PASSWORD=$(head -c 20 /dev/urandom | xxd -ps)

echo "Installation of system dependencies"
sudo apt-get -y install git python-dev python-virtualenv nodejs postgresql libpq-dev\
	supervisor npm libxml2-dev libxslt1-dev libmemcached-dev

if [ ! -f "$VIRTUALENV_DIR" ]; then
	echo "Initialization of virtualenv"
	mkdir -p $VIRTUALENV_DIR
	virtualenv --no-site-packages $VIRTUALENV_DIR
fi

source $VIRTUALENV_DIR/bin/activate

cd $PROJECT_DIR

echo "Installation of peep"

pip install -U peep

echo "Installation of pontoon dependencies"
peep install -r $PROJECT_DIR/requirements.txt

# Checks if environment has been initialized
if [ ! -f $PROJECT_DIR/.env ]; then
	echo "Setup of database"
	sudo -u postgres psql -c "CREATE USER pontoon WITH PASSWORD '$DB_PASSWORD' CREATEDB"
	sudo -u postgres psql -c "CREATE DATABASE pontoon WITH ENCODING 'utf-8' OWNER pontoon"
	echo "Copying sample .env file"
	cp $PROJECT_DIR/vagrant/env $PROJECT_DIR/.env
	sed -i "s:__secret_key__:$SECRET_KEY:g" .env
	sed -i "s:__hmac_key__:$HMAC_KEY:g" .env
	sed -i "s:__db_password__:$DB_PASSWORD:g" .env
fi

export DJANGO_SETTINGS_MODULE='pontoon.settings'

echo "Initialization of project schema"
$PROJECT_DIR/manage.py migrate

echo "Initialization of user accounts"
python -c "import dotenv; dotenv.read_dotenv()"\
          "from django.contrib.auth.models import User;"\
          "User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').exists()"
echo "Update of projects"
$PROJECT_DIR/manage.py update_projects

echo "Installation of node.js dependencies"
npm install

echo "Installation of pontoon as a service"
rm -rf /etc/supevisor/conf.d/
sudo ln -s $PROJECT_DIR/vagrant/supervisor/conf.d /etc/supervisor/conf.d
sudo supervisorctl update