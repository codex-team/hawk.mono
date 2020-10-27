[String]$collection = $args[0]

switch($collection) {
    "accounts" {
        echo "Restoring accounts data..."
        docker-compose exec -T mongodb mongorestore --host mongodb --drop -d hawk /dump/hawk_accounts
        break
    }
    "events" {
        echo "Restoring events data..."
        docker-compose exec -T mongodb mongorestore --host mongodb --drop -d hawk_events /dump/hawk_events
        break
    }
    default {
        Write-Error -Message "Please enter the name of the collection as the first parameter (accounts or events)." -Category InvalidArgument
        break
    }
}
