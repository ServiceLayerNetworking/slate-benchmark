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
	
    RunCPULoad(0, 0)
	WriteToFile("out.txt", 1024)
	fmt.Printf("Done running CPU Load. Now making HTTP calls\n")
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTheavy(c *gin.Context) {
    var data []byte
	
    RunCPULoad(0, 0)
	WriteToFile("out.txt", 10240)
	fmt.Printf("Done running CPU Load. Now making HTTP calls\n")
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}
