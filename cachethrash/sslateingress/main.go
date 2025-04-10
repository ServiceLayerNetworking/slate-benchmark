package main

import (
	"bytes"
	"crypto/rand"
	r2 "math/rand"
	"fmt"
	"strings"
	"log"
	"net/http"
	"io"
	"os"
    "runtime"
	"sync"
    "time"
	"github.com/gin-gonic/gin"
)

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled", "X-Slate-Start", "x-slate-start"}
var mut sync.Mutex

// generateMatrix creates an s x s matrix filled with random integers.
func generateMatrix(s int) [][]int {
	matrix := make([][]int, s)
	for i := range matrix {
		matrix[i] = make([]int, s)
		for j := range matrix[i] {
			matrix[i][j] = r2.Intn(100)
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
	rand.Read(data)
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
	return

	cpuPct := millicores / 10
	runFor := time.Duration(1000*cpuPct) * time.Microsecond
	sleepFor := time.Duration(1000*(100-cpuPct)) * time.Microsecond
	fmt.Printf("Worker sleepFor %s, runFor %s\n", sleepFor.String(), runFor.String())
	runtime.LockOSThread()
	// every milliseconds, run for runMicrosecond microseconds, and sleep for sleepMicrosecond microseconds

	ch := time.After(time.Duration(timeMillis) * time.Millisecond)
startLoop:
	for {
		select {
		case <-ch:
			runtime.UnlockOSThread()
			return
		default:
			begin := time.Now()
			for {
				select {
				case <-ch:
					fmt.Printf("Done\n")
					runtime.UnlockOSThread()
					return
				default:
					if time.Since(begin) > runFor {
						for {
							select {
							case <-ch:
								fmt.Printf("Done\n")
								runtime.UnlockOSThread()
								return
							case <-time.After(sleepFor):
								continue startLoop
							}
						}
					}

				}
			}
		}
	}
}

func main() {
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-handler, propogating %d headers", len(propogate))
	fmt.Printf("making go happy %s", bytes.NewBuffer([]byte("")))
	io.Copy(os.Stdout, strings.NewReader("Making go happy again"))
    r := gin.Default()

    r.GET("/getRecord/:record_id", GETgetRecord)



	r.Run(":8080")
}

func GETgetRecord(c *gin.Context) {
	record_id := c.Param("record_id") // <-- Extract record_id from path
	var data []byte

	RunCPULoad(0, 0)
	WriteToFile("out.txt", 0)
	fmt.Printf("Done running CPU Load. Now making HTTP calls\n")

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		defer wg.Done()
		var req *http.Request
		var resp *http.Response
		var err error
		var client *http.Client

		data = make([]byte, 0)
		rand.Read(data)
		client = &http.Client{}
		
		// Use dynamic URL based on record_id
		url := fmt.Sprintf("http://record-service:80/getRecord/%s", record_id)
		req, err = http.NewRequest("GET", url, nil)
		if err != nil {
			panic(err)
		}

		for _, v := range propogate {
			if val, ok := c.Request.Header[v]; ok {
				req.Header[v] = val
			}
		}
		req.URL.RawQuery = c.Request.URL.Query().Encode()
		resp, err = client.Do(req)
		if err != nil {
			fmt.Printf("Failed to make request: %v\n", err)
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			fmt.Printf("Failed to make request: %d\n", resp.StatusCode)
		}
		_, _ = io.ReadAll(resp.Body)
	}()

	wg.Wait()
	data = make([]byte, 0)
	rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
		fmt.Printf("Failed to truncate: %v", err)
	}
	c.Data(http.StatusOK, "application/octet-stream", data)
}
