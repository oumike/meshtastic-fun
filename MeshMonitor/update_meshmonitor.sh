sudo docker stop meshmonitor
sudo docker rm meshmonitor
sudo docker pull ghcr.io/yeraze/meshmonitor:latest
docker run -d --env-file ./meshmonitor.env --name meshmonitor -p 9090:3001 -v meshmonitor-data:/data ghcr.io/yeraze/meshmonitor:latest
