pip3 install -r requirements.txt
set -a allexport
. .environment
set +a allexport
> myapp.log
gunicorn main:app --daemon
