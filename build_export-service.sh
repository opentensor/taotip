cd ./taotip-export/client && yarn build
cd ../../ && docker-compose build export-service && docker-compose up export-service -d
