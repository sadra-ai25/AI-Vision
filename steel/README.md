if .env file not exist please done follow commands:
# cd project root
touch .env
sudo nano .env
# write bellow lines:
""" use for sadra database and uncomment that
DB_SERVER=192.168.50.113\sql2019
DB_NAME=dbailog
USERNAME=sa
PASSWORD=S@draAfzar

""" use for abhar database and uncomment related items
# DB_SERVER=192.168.1.11\sqlsadra
# DB_NAME=DBSadraafzar001
# USERNAME=AI
# PASSWORD=S@dra123

RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest