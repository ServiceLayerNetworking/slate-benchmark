package main

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

type processorResp struct {
	Anomalies string `json:"anomaliesDetected"`
}

type processorReq struct {
	Metrics []byte `json:"metrics"`
}

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled"}

func main() {
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-handler")
	r := gin.Default()
	r.GET("/detectAnomalies", DetectAnomalies)
	r.Run(":8080")
}

func DetectAnomalies(c *gin.Context) {
	// call metrics processing service
	// return whether anomaly was detected
	data := make([]byte, 1*1024*1024)
	rand.Read(data)

	client := &http.Client{}
	req, err := http.NewRequest("POST", "http://metrics-processing:8000/detectAnomalies", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}

	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
			fmt.Printf("header: %v: %v\n", v, val)
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	_, err = client.Do(req)
	if err != nil {
		panic(err)
	}

	c.JSON(200, gin.H{
		"anomaliesDetected": r.Anomalies,
	})
}
