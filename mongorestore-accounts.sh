#!/bin/bash

if [ $# -eq 0 ]
then
    result=$(docker-compose exec -T mongodb sh -c "ls -tr /dump/hawk_prod_mongodb-accountants_daily-full*.gz | head -1")
    if [ -z "$result" ]
    then
        echo "No arguments supplied. Usage: ./mongorestore-accounts.sh /dump/backup.gz"
        exit 1
    fi
else
    result=$(docker-compose exec -T mongodb sh -c "ls -tr $1 | head -1")
    if [ -z "$result" ]
    then
        echo "No such file. Check that you placed it into the mounted folder ./dump"
        exit 1
    fi
fi

docker-compose exec -T mongodb mongorestore --host mongodb --drop --archive=$result
