package main

import (
	"bytes"
	"crypto/rand"
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
	if millicores == 0 {
		return
	}

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

    r.POST("/light", POSTlight)
    r.POST("/heavy", POSTheavy)


	r.Run(":8080")
}



func POSTlight(c *gin.Context) {
    var data []byte
	
    RunCPULoad(20, 8)
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
		req, err = http.NewRequest("POST", "http://s6f83:8080/light", bytes.NewBuffer(data))
		if err != nil {
			panic(err)
		}
		for _, v := range propogate {
			if val, ok := c.Request.Header[v]; ok {
				req.Header[v] = val
			}
		}
		req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
		resp, err = client.Do(req)
		if err != nil {
			fmt.Printf("Failed to make request: %v", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			fmt.Printf("Failed to make request: %d", resp.StatusCode)
		}
		_, _ = io.ReadAll(resp.Body)
		//fmt.Printf("Response: %s\n", string(bodyB))
		
	}()
	
	wg.Wait()
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTheavy(c *gin.Context) {
    var data []byte
	
    RunCPULoad(200, 8)
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
		req, err = http.NewRequest("POST", "http://s6f83:8080/heavy", bytes.NewBuffer(data))
		if err != nil {
			panic(err)
		}
		for _, v := range propogate {
			if val, ok := c.Request.Header[v]; ok {
				req.Header[v] = val
			}
		}
		req.Header.Set("Content-Length", fmt.Sprintf("%d", len(data)))
		resp, err = client.Do(req)
		if err != nil {
			fmt.Printf("Failed to make request: %v", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			fmt.Printf("Failed to make request: %d", resp.StatusCode)
		}
		_, _ = io.ReadAll(resp.Body)
		//fmt.Printf("Response: %s\n", string(bodyB))
		
	}()
	
	wg.Wait()
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}
