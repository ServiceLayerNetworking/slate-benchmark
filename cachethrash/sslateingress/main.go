package main

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	// "sync"

	mr "math/rand"

	"github.com/gin-gonic/gin"
)

var propogate = []string{
	"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid",
	"X-B3-ParentSpanid", "X-B3-Sampled",
	"X-Slate-Start", "x-slate-start",
}

// generateMatrix creates an s x s matrix filled with math random integers.
func generateMatrix(s int) [][]int {
	matrix := make([][]int, s)
	for i := range matrix {
		matrix[i] = make([]int, s)
		for j := range matrix[i] {
			matrix[i][j] = mr.Intn(100)
		}
	}
	return matrix
}

// multiplyMatrices multiplies two matrices and returns the resultant matrix.
func multiplyMatrices(m1, m2 [][]int) [][]int {
	s := len(m1)
	result := make([][]int, s)
	for i := 0; i < s; i++ {
		result[i] = make([]int, s)
		for j := 0; j < s; j++ {
			for k := 0; k < s; k++ {
				result[i][j] += m1[i][k] * m2[k][j]
			}
		}
	}
	return result
}

func WriteToFile(filename string, fileSize int) {
	if fileSize == 0 {
		return
	}
	file, err := os.Create(filename)
	if err != nil {
		file, err = os.Open(filename)
		if err != nil {
			fmt.Printf("failed to open file: %v\n", err)
			return
		}
	}
	data := make([]byte, fileSize)
	rand.Read(data) // crypto/rand
	if _, err := file.Write(data); err != nil {
		fmt.Printf("failed to write to file: %v\n", err)
	}
}

func RunCPULoad(millicores int, timeMillis int) {
	if millicores == 0 || timeMillis == 0 {
		return
	}
	m1 := generateMatrix(timeMillis)
	m2 := generateMatrix(timeMillis)
	_ = multiplyMatrices(m1, m2)
}

func main() {
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-handler, propagating %d headers", len(propogate))
	fmt.Printf("making go happy %s\n", bytes.NewBuffer([]byte("")))
	io.Copy(os.Stdout, strings.NewReader("Making go happy again\n"))

	r := gin.Default()
	r.GET("/getRecord", GETgetRecord)
	r.Run(":8080")
}

func GETgetRecord(c *gin.Context) {
	recordID := c.Query("record_id") // ✅ Extract from query param

	if recordID == "" {
		c.String(http.StatusBadRequest, "Missing record_id")
		return
	}

	// RunCPULoad(0, 0)
	// WriteToFile("out.txt", 0)
	fmt.Println("Done running CPU Load. Now making HTTP calls")

	// var wg sync.WaitGroup
	// wg.Add(1)

	func() {
		// defer wg.Done()

		data := make([]byte, 0)
		rand.Read(data)

		client := &http.Client{}
		url := fmt.Sprintf("http://record-service:80/getRecord?record_id=%s", recordID)

		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			log.Printf("Failed to create request: %v", err)
			return
		}

		// Propagate headers
		for _, h := range propogate {
			if val, ok := c.Request.Header[h]; ok {
				req.Header[h] = val
			}
		}

		resp, err := client.Do(req)
		if err != nil {
			log.Printf("Failed to make request: %v", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			log.Printf("Upstream request failed with status: %d", resp.StatusCode)
		}

		_, _ = io.ReadAll(resp.Body)
	}()

	// wg.Wait()

	// finalData := make([]byte, 0)
	// rand.Read(finalData)

	// if err := os.Truncate("out.txt", 0); err != nil {
	// 	log.Printf("Failed to truncate file: %v", err)
	// }

	c.Data(http.StatusOK, "application/octet-stream", make([]byte, 0))
}
