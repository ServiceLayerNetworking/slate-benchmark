package main

import (
	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()
	r.POST("/detectAnomalies", DetectAnomalies)
	r.Run(":8080")

}

func DetectAnomalies(c *gin.Context) {
	//promUrl := "http://10.244.0.31:9090/api/v1/query?query=istio_requests_total"
	//resp, err := http.Get(promUrl)
	//if err != nil {
	//	c.JSON(500, gin.H{
	//		"anomaliesDetected": "error",
	//	})
	//	return
	//}
	//// save body to string
	//body, err := ioutil.ReadAll(resp.Body)
	//if err != nil {
	//	c.JSON(500, gin.H{
	//		"anomaliesDetected": "error",
	//	})
	//	return
	//}
	//fmt.Printf("Prometheus response code: %v, body len: %v\n", resp.StatusCode, len(body))
	//time.Sleep(1 * time.Second)

	// we'll assume there are always no anomalies
	c.JSON(500, gin.H{
		"anomaliesDetected": "false",
	})
}
