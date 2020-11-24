#!/bin/bash

# show usage help
display_usage() {
    echo -e "\nUsage:\n./mongorestore-accounts.sh [argument] \n"
    echo -e "Argument can be \n1. Empty – load latest .gz file from ./dump directory"
    echo -e "2. pull – download latest .gz file from s3 storage, save to ./dump directory and load"
    echo -e "3. <filename> - load dump from <filename>"
}

# run mongorestore with docker-compose for mongodb database
restore_dump() {
    echo "Load $1"
    docker-compose exec -T mongodb mongorestore --host mongodb --drop --archive=$1
    exit 0
}

# pull latest dump from s3 storage
pull_latest() {
    source .env
    if [ -z "$s3_basic_auth" ]
    then
        echo "Place s3_basic_auth variable to the .env file"
        exit 1
    fi

    curl -s -u $s3_basic_auth http://s3.hawk.so/hawk_prod_mongodb-accountants_daily-full_latest.gz -o ./dump/hawk_prod_mongodb-accountants_daily-full_latest.gz
    if [ ! -f "./dump/hawk_prod_mongodb-accountants_daily-full_latest.gz" ]
    then
        echo "Cannot download file. Check s3_basic_auth variable in the .env file"
        exit 1
    fi

    restore_dump "./dump/hawk_prod_mongodb-accountants_daily-full_latest.gz"
    exit 0
}

# Executed without arguments – load latest .gz file from ./dump directory
if [ $# -eq 0 ]
then
    result=$(docker-compose exec -T mongodb sh -c "ls -t /dump/hawk_prod_mongodb-accountants_daily-full*.gz | head -1")
    if [ -z "$result" ]
    then
        echo "Not found any gz file in ./dump directory"
        display_usage
        exit 1
    fi
    restore_dump $result
fi

# Display usage
if [[ ( $1 == "--help") || ($1 == "-h") ]]
then 
    display_usage
    exit 0
fi

# Pull – download latest .gz file from s3 storage, save to ./dump directory and load
if [[ $1 == "pull" ]]
then
    pull_latest
fi

# Load from file dump
if [ -f "$1" ]
then
    restore_dump $1
else
    echo "No such file. Check that you placed it into the mounted folder ./dump"
    display_usage
fi