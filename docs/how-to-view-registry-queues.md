# How to view Registry queues

This document describes how to view what queues we have in Registry and what tasks they have.

First of all, not that the Registry is actually RabbitMQ.

## 1. Open Rabbit MQ GUI

1. Go to http://localhost:15672 — the port can be learned from docker-compose.yml under `rabbitmq` section
2. Authorise using `guest:guest` pair

## 2. View available queues

They are listed under `Queues` tab

![](https://capella.pics/1d96b75d-40e9-4c48-bfba-6ddd01c5a138.jpg)

You can see how many messages you have in each queue.

## 3. View message in queue

1. Click on queue name 
2. Click on the `Get Message(s)` button
