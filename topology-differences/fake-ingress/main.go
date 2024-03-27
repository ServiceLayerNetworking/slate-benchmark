package main

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"github.com/gin-gonic/gin"
	"io/ioutil"
	"net/http"
)

func MakeRequestWithSize(endpoint string, callsize int) {
	data := make([]byte, callsize)
	rand.Read(data)
	client := &http.Client{}
	req, err := http.NewRequest("GET", fmt.Sprintf(endpoint), bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	resp, err := client.Do(req)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
}

type processorResp struct {
	Anomalies string `json:"anomaliesDetected"`
}

type processorReq struct {
	Metrics []byte `json:"metrics"`
}

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled"}

func main() {
	r := gin.Default()
	r.POST("/users/add", HandleUserAddition)
	r.POST("/users/permission", HandleUserPermission)
	r.Run(":8080")
}

func HandleUserAddition(c *gin.Context) {

}

func HandleUserPermission(c *gin.Context) {

}

func ForwardRequest(c *gin.Context) {
	// call metrics processing service
	// return whether anomaly was detected
	data := make([]byte, 5*1024)
	rand.Read(data)
	//r := &processorReq{
	//	Metrics: data,
	//}
	client := &http.Client{}
	req, err := http.NewRequest("GET", "http://metrics-handler:8000/detectAnomalies", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	// propogate tracing headers
	fmt.Printf("ForwardRequest is called")
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
			fmt.Printf("header: %v: %v\n", v, val)
		}
	}
	resp, err := client.Do(req)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	// save body to string
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}
	r := &processorResp{}
	if err = json.Unmarshal(body, r); err != nil {
		r.Anomalies = "error"
	}
	fmt.Printf("detected: %v\n", r.Anomalies)
	c.JSON(200, gin.H{
		"anomaliesDetected": r.Anomalies,
	})
}
