# How to get events on local hawk

If you need to get event on the local version on Hawk, follow these steps.

## 1. Make sure that project is successfully runs.

1. Go to hawk.mono root 
2. Run `docker-compose up`
3. Wait till all containers will run
4. Open other terminal tab and run `docker ps` or open Kitematic and press CMD+R to refresh containers list
5. You should see at least five containers: 
  - `hawkmono_collector`
  - `hawkmono_garage`
  - `rabbitmq:3-management`
  - `hawkmono_api`
  - `mongo`

If you don't see one or several containers, it means they are not running. 
Probably, some error occurs — you should resolve them first.

## 2. Make sure the Garage is ready

1. Go to http://localhost:8080 
2. You should see the Garage
3. If you don't authorised, you need to log into your account.

## 3. Get an Integration Token

If you already have a workspace and projects, go to some project's settings 
(by clicking on project's name or image at the header of main column)
and open an Integrations page. You will find your `Integration Token` there.

If you don't have a projects yes, create one:

1. Click on the [+] button at the left Workspaces.
2. Create a Workspace
3. Click on the created workspace at the left column.
4. Click on the blue [+] button to add a new Project
5. Add a new Project
6. Click on the new created project, select a Catcher
7. Copy your `Integration Token` from the Catcher Instructions page

![](https://capella.pics/65608213-f333-4977-9da5-b64c5af7afda.jpg)

## 4. Run JavaScript catcher testing page

1. From the `hawk.mono` directory go to `catchers/javascirpt` directory
2. Make sure you are on `master` branch. Switch to `master` branch if you are on any other branch.
3. Open `example/index.html` in your IDE and put an Integration Token to the initialization of HawkCatcher at `token` property:

![](https://capella.pics/3c24e9c0-b8a8-40b3-a291-ef00991138ff.jpg)

4. Go back to terminal, make sure you are still in the `catchers/javascirpt` directory
5. Run `yarn` to install dependencies
6. Run `yarn dev` to run testing page
7. You should see the testing page on `http://localhost:9000` or something like that.

## 5. Make sure that Catcher is connected to the Collector

1. On the testing page, open JS Console — there should be no errors
2. Go to `Network` tab and make sure there is a WebSocket connection called `ws` (not a `websocket`)

![](https://capella.pics/5f400b8b-3590-4ff7-b5ef-a0386a30ae89.jpg)

Now you can send events to the Collector by clicking on buttons on testing page. 

3. Click on the `hawk.test()` button.

![](https://capella.pics/c29f7584-d674-499c-830c-59272fdbad7d.jpg)

## 6. Make sure that Collector accepts events and pass them to the Registry

If the Collector works properly, it should handle the event we just sent and add a new task for processing it to the **Registry**.
So we need to check if there is an unprocessed task in a Registry's queue (that is actual Rabbit MQ queue). 

1. Open Rabbit MQ GUI: http://localhost:15672
2. Authorise using `guest:guest` pair
3. Go to `Queues` tab
4. Take a look at the `errors/javascript` queue — there **should** be at least one message.

![](https://capella.pics/5b7a0364-c9be-4e93-b1b9-2e18a5406e9b.jpg)  

_If you are interested in, you can discover message details by clicking on `errors/javascript` queue and then on `Get Message(s)` button._ 

## 7. Run Workers that will process tasks from Registry.

To handle JavaScript error events you need at least two workers:

- `JavaScript Worker` will process an event, validate data and structure, then pass prepared event to the Grouper Worker for saving to DB.
- `Grouper Worker` will check for the first-occurrence/repetition logic and save event to the corresponding collection in Events DB.

1. Go to `hawk.mono/workers` directory in terminal.
2. If you did not install dependencies there, run `yarn`
3. Run `yarn run-js` to run the `JavaScript Worker`

Now let's see that JavaScript Worker successfully process the event and add a new task to the Grouper Worker.

4. Open Rabbit MQ GUI and go to `Queues` tab
5. Take a look at the `grouper` queue — there **should** be at least one message waiting for handle.

Ok, let's run the Grouper Worker

6. Open new terminal tab (CMD+T) with the same directory (`hawk.mono/workers`)
7. Run `yarn run-grouper` to run the `Grouper Worker`

If you will refresh Queues list in RabbitMQ GUI, you should see that the message from `grouper` queue has left.  

## 8. Check the event in the Events DB

In previous part, the Grouper Worker should save the event to the Events DB. Lets find it there.

1. Open one of MongoDB GUI, for example [Compass](https://www.mongodb.com/products/compass) 
2. Connect to the local mongo (defaults are — host: `localhost`, port: `27017`)
3. Make sure there are `hawk_events` database
4. Open `hawk_events` database
5. Open `events:<projectId>` collection
6. You should see the event we just insert 

![](https://capella.pics/2a5feb41-95a7-4943-9572-fbe48e9d0325.jpg)

## 9. Check the Garage for new event

Open the Garage on Project's page. The testing event `Hawk JavaScript Catcher test message.` should be there.

![](https://capella.pics/1b48e631-84fe-407e-997c-a7d0d7d0a36c.jpg)
