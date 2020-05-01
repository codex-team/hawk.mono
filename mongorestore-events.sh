#!/bin/bash

docker-compose exec -T mongodb mongorestore --host mongodb --drop -d hawk_events /dump/hawk_events
