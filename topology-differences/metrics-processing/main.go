package main

import (
	"bytes"
	"fmt"
	"github.com/gin-gonic/gin"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
)

func main() {
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-processing")
	r := gin.Default()
	r.POST("/detectAnomalies", DetectAnomalies)
	r.Run(":8080")

}

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled"}

func DetectAnomalies(c *gin.Context) {
	log.Printf("Calling metrics-db\n")
	promUrl := "http://metrics-db:8080/dbcall"
	client := &http.Client{}
	req, err := http.NewRequest("GET", promUrl, bytes.NewBuffer([]byte("")))
	if err != nil {
		panic(err)
	}
	// propogate tracing headers
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
			fmt.Printf("header: %v: %v\n", v, val)
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", 0))
	req.Header.Set("x-slate-routeto", "us-east-1")
	resp, err := client.Do(req)
	log.Printf("Calling metrics-db\n")
	fmt.Printf("[fmt] Calling metrics-db\n")
	if err != nil {
		log.Printf("erorr calling metrics-db")
		c.JSON(500, gin.H{
			"anomaliesDetected": "error",
		})
		return
	}
	// save body to string
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Printf("couldn't read body")
		c.JSON(500, gin.H{
			"anomaliesDetected": "error",
		})
		return
	}
	fmt.Printf("Prometheus response code: %v, body len: %v\n", resp.StatusCode, len(body))

	// we'll assume there are always no anomalies
	//fmt.Printf("REQUEST HEADERS: %v", c.Request.Header)
	var fiveThousandAs string = strings.Repeat("a", 10)
	c.JSON(500, gin.H{
		"anomaliesDetected": "false",
		"data":              fiveThousandAs,
	})
}
