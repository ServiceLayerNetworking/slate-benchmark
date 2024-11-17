package main

import (
	"bytes"
	// "crypto/rand"
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

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-TraceId", "X-B3-Spanid", "X-B3-SpanId", "X-B3-ParentSpanid", "X-B3-ParentSpanId", "X-B3-Sampled", "X-Slate-Start", "X-Slate-1mb-Writes"}
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

    r.POST("/cart", POSTcart)
    r.POST("/cart/empty", POSTcartempty)
    r.POST("/cart/checkout", POSTcartcheckout)
    r.POST("/setCurrency", POSTsetCurrency)
	r.POST("/singlecore", POSTSingleCore)
	r.POST("/multicore", POSTMultiCore)


	r.Run(":8080")
}



func POSTcart(c *gin.Context) {
    var data []byte
	
	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	
	data = make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://frontend:80/cart", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)		
	
	data = make([]byte, 0)
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTcartempty(c *gin.Context) {
	
	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	data := make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://frontend:80/cart/empty", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)
		//fmt.Printf("Response: %s\n", string(bodyB))
			
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTcartcheckout(c *gin.Context) {
    var data []byte

	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	
	data = make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://frontend:80/cart/checkout", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)
	
	data = make([]byte, 0)
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTsetCurrency(c *gin.Context) {
    var data []byte
	
   
	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	
	data = make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://frontend:80/setCurrency", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)
	
	data = make([]byte, 0)
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTSingleCore(c *gin.Context) {
    var data []byte
	
   
	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	
	data = make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://corecontrast:8080/singlecore", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)
	
	data = make([]byte, 0)
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTMultiCore(c *gin.Context) {
    var data []byte
	
   
	var req *http.Request
	var resp *http.Response
	var err error
	var client *http.Client
	
	data = make([]byte, 0)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://corecontrast:8080/multicore", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	
	req.URL.RawQuery = c.Request.URL.Query().Encode()
	resp, err = client.Do(req)
	if err != nil {
		fmt.Printf("Failed to make request: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Failed to make request: %d", resp.StatusCode)
		c.Data(http.StatusInternalServerError, "application/octet-stream", data)
		return
	}
	_, _ = io.ReadAll(resp.Body)
	
	data = make([]byte, 0)
    c.Data(http.StatusOK, "application/octet-stream", data)
}
