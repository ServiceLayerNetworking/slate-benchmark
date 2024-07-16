
go build -o topogen main.go

./topogen -topology="topologies/bufferbloater.yaml" -experiment="bufferbloater" -registry="ghcr.io/gangmuk" -build=true
