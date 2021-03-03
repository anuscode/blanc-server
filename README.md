# how to deploy.

1. sudo apt-get update
2. sudo apt-get upgrade
3. sudo apt-get install docker docker-compose
4. cd [BLANC-PROJECT-ROOT-PATH]
5. sudo docker-compose -f [YAML_FILE] build
6. sudo docker-compose -f [YAML_FILE] up

# how to check logs.

1. sudo docker-compose up -d -> create images and run it
2. sudo docker container ls -> will show you the container id
3. sudo docker logs [container_id]
