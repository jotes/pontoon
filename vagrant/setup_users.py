#!/usr/bin/env python

from django.contrib.auth.models import User

if User.objects.filter(username='admin').exists()
