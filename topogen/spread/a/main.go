package main

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"time"

	"github.com/gin-gonic/gin"
)

var propogate = []string{"X-Request-Id", "X-B3-Traceid", "X-B3-Spanid", "X-B3-ParentSpanid", "X-B3-Sampled"}

func WriteToFile(filename string, fileSize int) {
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

func RunCPULoad(millicoreCount int, timeMillis int) {
	if timeMillis == 0 || millicoreCount == 0 {
		return
	}

	// 500 millicore -> 500 microseconds
	runFor := time.Duration(millicoreCount) * time.Microsecond
	sleepFor := time.Duration(1000-millicoreCount) * time.Microsecond

	runtime.LockOSThread()
	// make timer
	timer := time.NewTimer(time.Duration(timeMillis) * time.Millisecond)
	d := time.Duration(timeMillis) * time.Millisecond

	fmt.Printf("Timer duration %s, sleepFor %s, runFor %s\n", d.String(), sleepFor.String(), runFor.String())
	fmt.Printf("starting load for %dms, current time %d\n", timeMillis, time.Now().UnixMilli())
	for {
		select {
		case <-timer.C:
			fmt.Printf("finished load at for %dms, current time %d\n", timeMillis, time.Now().UnixMilli())
			runtime.UnlockOSThread()
			return
		default:
			begin := time.Now()
			for {
				if time.Since(begin) > runFor {
					break
				}
			}
			time.Sleep(sleepFor)
		}
	}
}

func main() {
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-handler, propogating %d headers", len(propogate))
	fmt.Printf("making go happy %s", bytes.NewBuffer([]byte("")))
	r := gin.Default()

	r.POST("/spreada", POSTspreada)

	r.Run(":8080")
}

func POSTspreada(c *gin.Context) {
	var data []byte
	RunCPULoad(0, 0)
	WriteToFile("/dev/null", 1048576)
	fmt.Printf("Done running CPU Load. Now making HTTP calls\n")

	var req *http.Request
	var err error
	var client *http.Client

	data = make([]byte, 0)
	rand.Read(data)
	client = &http.Client{}
	req, err = http.NewRequest("POST", "http://b:8080/spreadb", bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}
	for _, v := range propogate {
		if val, ok := c.Request.Header[v]; ok {
			req.Header[v] = val
		}
	}
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
	_, err = client.Do(req)
	if err != nil {
		panic(err)
	}

	data = make([]byte, 0)
	rand.Read(data)
	c.Data(http.StatusOK, "application/octet-stream", data)
}
