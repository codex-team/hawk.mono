# How to work with a hawk.mono

This guide will help you to run Hawk locally for a development needs:

- project structure
- how to clone the repo and run
- how to update and rebuild containers

Let's go!

## Structure

...

## Installation

How to clone the repo and run containers.

### Preparation

You need to create a new chat in Telegram with a [@codex_bot](https://t.me/codex_bot)
to get notifications and any code errors from local's Hawk.

#### Telegram

`New Group` -> `Enter a name` -> `Add @codex_bot`

Then use command `/notify` in chat to get a webhook for notifications.

Use it in `.env` files as `CODEX_BOT_WEBHOOK` param where it needs.

#### Hawk Token

Go to [garage.hawk.so](https://garage.hawk.so/), create a new project
and get a token.

Use it in `.env` files as `HAWK_TOKEN` or `HAWK_CATCHER_TOKEN` param where it needs.

### Getting sources

Clone the repo.

```
git clone https://github.com/codex-team/hawk.mono
```

Init and pull submodules.

```
git submodule init && git submodule update
```

Now you have a complete structure for all folders.

You can check it by entering the `api` folder.
If it is not an empty then you may go next step.

### Setting up env files 

You should create a few `.env` files according to their samples `.sample` or `.docker`. 

<details><summary><code>accounting/.env.sample</code> -> <code>accounting/.env</code></summary><p>
- HAWK_CATCHER_TOKEN
</p></details>

<details><summary><code>api/.env.sample</code> -> <code>api/.env</code></summary><p>
To enable email sending from the server use your email keys.

- SMTP_USERNAME=user@hawk.so
- SMTP_PASSWORD=mySecretPwd
- SMTP_SENDER_NAME=Hawk local
- SMTP_SENDER_ADDRESS=user@hawk.so

- HAWK_CATCHER_TOKEN
- TELEGRAM_MAIN_CHAT_URL
- TELEGRAM_MONEY_CHAT_URL
</p></details>

<details><summary><code>collector/.env.docker</code> -> <code>collector/.env</code></summary><p>
- HAWK_TOKEN
- NOTIFY_URL
</p></details>

<details><summary><code>cron-manager/config.sample.yml</code> -> <code>cron-manager/config.yml</code></summary><p>
Just copy the file.
</p></details>

<details><summary><code>garage/.env.sample</code> -> <code>garage/.env</code></summary><p>
- VUE_APP_HAWK_TOKEN
</p></details>

<details><summary><code>workers/.env.sample</code> -> <code>workers/.env</code></summary><p>
- MONGO_ACCOUNTS_DATABASE_URI=mongodb://mongodb:27017/hawk
- MONGO_EVENTS_DATABASE_URI=mongodb://mongodb:27017/hawk_events
- HAWK_CATCHER_TOKEN
- CODEX_BOT_WEBHOOK
</p></details>

<details><summary><code>workers/workers/archiver/.env.sample</code> -> <code>workers/workers/archiver/.env</code></summary><p>
- REPORT_NOTIFY_URL
- REGISTRY_URL=amqp://guest:guest@rabbitmq
</p></details>

<details><summary><code>workers/workers/email/.env.sample</code> -> <code>workers/workers/email/.env</code></summary><p>
- SMTP_USERNAME=user@hawk.so
- SMTP_PASSWORD=mySecretPwd
- SMTP_SENDER_NAME=Hawk local worker
- SMTP_SENDER_ADDRESS=user@hawk.so
</p></details>

<details><summary><code>workers/workers/grouper/.env.sample</code> -> <code>workers/workers/grouper/.env</code></summary><p>
Just copy the file.
</p></details>

<details><summary><code>workers/workers/limiter/.env.sample</code> -> <code>workers/workers/limiter/.env</code></summary><p>
- REPORT_NOTIFY_URL
</p></details>

<details><summary><code>workers/workers/paymaster/.env.sample</code> -> <code>workers/workers/paymaster/.env</code></summary><p>
- REPORT_NOTIFY_URL
</p></details>

<details><summary><code>workers/workers/sender/.env.sample</code> -> <code>workers/workers/sender/.env</code></summary><p>
Just copy the file.
</p></details>


### Create a needed dirs

```
mkdir dump
```

### Starting containers

The moment of truth. Running containers from `docker-compose.yml` file. 

```
docker compose up 
```

### Post running

Apply api database migration.

```
docker-compose exec api yarn migrate-mongo up
```

### Run the site

Go to [localhost:8080](http://localhost:8080/) and see the Hawk's log in page.

Sign in for the first time and you'll get a password to your email.

### Run workers

Go to `workers` dir

```
cd workers
```

Run all workers

```
docker-compose -f docker-compose.dev.yml up
```

## Updates

...

## Dashboards

### Rabbit MQ Management board

Go to [localhost:15672](http://localhost:15672)

user: `guest`

pass: `guest`

### MongoDB

You can use [MongoDB Compass](https://www.mongodb.com/try/download/compass) GUI app to access database.

Connection string: `mongodb://localhost:27017/`.

### Redis

You can use [RedisInsight](https://redislabs.com/redis-enterprise/redis-insight/) GUI to access database.

Host: `localhost`

Port: `6379`

Name: `Hawk Local`
