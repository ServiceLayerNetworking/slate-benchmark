package main

import (
	"io/ioutil"
	"net/http"
    //"fmt"
    //"encoding/json"
	"github.com/gin-gonic/gin"
)

const flaskServerURL = "http://matmul-compute:8000/compute"

type MatrixResponse struct {
//    MatrixA [][]float64 `json:"Matrix A"`
//    MatrixB [][]float64 `json:"Matrix B"`
    Result  [][]float64 `json:"Result"`
    matmul_time  float64 `json:"matmul_time"`
}

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled"}

func main() {
	r := gin.Default()

	r.GET("/compute", LightCompute)
	r.POST("/compute", HeavyCompute)

	// Run the server
	r.Run(":8080") // listen and serve on 0.0.0.0:8080
}


func LightCompute(c *gin.Context) {
		// Extract 'row' and 'column' from query parameters
		row := c.Query("row")
		column := c.Query("column")

		// Forward request to Flask server
		client := &http.Client{}
		req, err := http.NewRequest("GET", flaskServerURL, nil)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// Set headers
		req.Header.Set("row", row)
		req.Header.Set("column", column)

		// propogate tracing headers
		for _, v := range propogate {
			if val, ok := c.Request.Header[v]; ok {
				req.Header[v] = val
			}
		}

		// Make the request
		resp, err := client.Do(req)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		defer resp.Body.Close()

		// Read the response
		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// Send the response
		c.Data(http.StatusOK, "application/json", body)
	}

func HeavyCompute(c *gin.Context) {
		// Extract 'row' and 'column' from query parameters
		row := c.Query("row")
		column := c.Query("column")

		// Forward request to Flask server
		client := &http.Client{}
		req, err := http.NewRequest("POST", flaskServerURL, nil)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// Set headers
		req.Header.Set("row", row)
		req.Header.Set("column", column)

		// propogate tracing headers
		for _, v := range propogate {
			if val, ok := c.Request.Header[v]; ok {
				req.Header[v] = val
			}
		}

		// Make the request
		resp, err := client.Do(req)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		defer resp.Body.Close()

		// Read the response
		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// Send the response
		c.Data(http.StatusOK, "application/json", body)
	}
