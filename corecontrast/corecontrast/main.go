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
	"strconv"
	"sync"
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

func main() {
	// runtime.GOMAXPROCS(1)
	gin.DefaultWriter = os.Stdout
	log.Printf("Starting metrics-handler, propogating %d headers", len(propogate))
	fmt.Printf("making go happy %s", bytes.NewBuffer([]byte("")))
	io.Copy(os.Stdout, strings.NewReader("Making go happy again"))	
    r := gin.Default()

    r.POST("/singlecore", POSTSingleCore)
	r.POST("/multicore", POSTMultiCore)

	r.Run(":8080")
}



func POSTSingleCore(c *gin.Context) {
	mut.Lock()
	defer mut.Unlock()
    var data []byte
	
	n := 20
	hdr := c.GetHeader("X-Slate-1mb-Writes")
	if val, err := strconv.Atoi(hdr); err == nil {
		n = val
	} else {
		fmt.Printf("Failed to convert header value (%v) to int: %v", hdr, err)
	}
    // RunCPULoad(0, 0)
	for i := 0; i < n; i++ {
		if i == n - 1 {
			WriteToFile("out.txt", 1024 * 1024 * 1)
		} else {
			WriteToFile("out.txt", 1024 * 1024 * 1)
		}
	}
	fmt.Printf("Done running CPU Load (%v writes). Now making HTTP calls\n", n)
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}

func POSTMultiCore(c *gin.Context) {
    var data []byte
	
    // RunCPULoad(0, 0)
	WriteToFile("out.txt", 1024 * 1024 * 0.5)
	fmt.Printf("Done running CPU Load. Now making HTTP calls\n")
	data = make([]byte, 0)
    rand.Read(data)
	if err := os.Truncate("out.txt", 0); err != nil {
    	fmt.Printf("Failed to truncate: %v", err)
	}
    c.Data(http.StatusOK, "application/octet-stream", data)
}
