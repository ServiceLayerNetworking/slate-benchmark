package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"io/ioutil"
	"net/http"
)

func main() {
	r := gin.Default()
	r.POST("/detectAnomalies", DetectAnomalies)
	r.Run(":8080")

}

func DetectAnomalies(c *gin.Context) {
	promUrl := "http://metrics-db:8080/dbcall"
	resp, err := http.Get(promUrl)
	if err != nil {
		c.JSON(500, gin.H{
			"anomaliesDetected": "error",
		})
		return
	}
	// save body to string
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		c.JSON(500, gin.H{
			"anomaliesDetected": "error",
		})
		return
	}
	fmt.Printf("Prometheus response code: %v, body len: %v\n", resp.StatusCode, len(body))

	// we'll assume there are always no anomalies
	//fmt.Printf("REQUEST HEADERS: %v", c.Request.Header)
	//var fiveThousandAs string = strings.Repeat("a", 10)
	//c.JSON(500, gin.H{
	//	"anomaliesDetected": "false",
	//	"data":              fiveThousandAs,
	//})
}
