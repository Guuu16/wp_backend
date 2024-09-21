django-admin startapp loginAndLogout apps/loginAndLogout

python manage.py makemigrations

python manage.py migrate

python manage.py crontab add

python manage.py crontab run  crontab_id

python manage.py crontab remove

find ./ -name "*.pyc" | xargs rm -rf

gunicorn webportal.wsgi -w 4 -b 0.0.0.0:5555 --access-logfile access.log --error-logfile error.log

* [api doc link](web_pro_api.md)


![CleanShot 2024-09-21 at 23 19 15@2x](https://github.com/user-attachments/assets/5c0ea1bd-8bf9-434e-a629-a36349ad2e8b)
