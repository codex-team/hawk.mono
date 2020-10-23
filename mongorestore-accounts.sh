#!/bin/bash

docker-compose exec -T mongodb mongorestore --host mongodb --drop -d hawk ./dump/hawk_accounts
