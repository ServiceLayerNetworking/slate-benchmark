package main

import (
	"fmt"
	"math"
	"math/rand"
	"os"
	"runtime"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

var perRequestCPUDuration time.Duration

func init() {
	// Limit the Go scheduler to a single OS thread
	runtime.GOMAXPROCS(1)

	// Seed the RNG for log-normal sampling
	rand.Seed(time.Now().UnixNano())

	// Compute how much CPU time each request should burn
	rpsStr := getEnv("RPS_SATURATE", "800")
	rps, err := strconv.Atoi(rpsStr)
	if err != nil || rps <= 0 {
		fmt.Printf("Invalid RPS_SATURATE=%s; defaulting to 800 RPS\n", rpsStr)
		rps = 800
	}
	perRequestCPUDuration = time.Second / time.Duration(rps)
}

// Cache simulates an LRU cache with log‑normal DB latency on cache misses.
type Cache struct {
	data      map[string]struct{}
	order     []string
	lock      sync.Mutex
	cacheSize int

	// Log-normal DB latency parameters:
	dbMeanMs float64 // desired mean latency in milliseconds
	dbSigma  float64 // standard deviation in log-space
}

// NewCache creates a Cache of the given size, with a log‑normal DB latency
// distribution of mean dbMean and log‑stddev dbSigma.
func NewCache(size int, dbMean time.Duration, dbSigma float64) *Cache {
	return &Cache{
		data:      make(map[string]struct{}),
		order:     make([]string, 0, size),
		cacheSize: size,
		dbMeanMs:  float64(dbMean) / float64(time.Millisecond),
		dbSigma:   dbSigma,
	}
}

func (c *Cache) Get(recordID string) (string, bool) {
	// 1) Try cache under lock
	c.lock.Lock()
	if _, found := c.data[recordID]; found {
		c.moveToEnd(recordID)
		c.lock.Unlock()
		return "cache", true
	}
	c.lock.Unlock()

	// 2) Simulate a log‑normal DB call latency *without* holding the lock
	time.Sleep(c.sampleLogNormal())

	// 3) Insert into cache under lock
	c.lock.Lock()
	defer c.lock.Unlock()
	if len(c.data) >= c.cacheSize {
		oldest := c.order[0]
		c.order = c.order[1:]
		delete(c.data, oldest)
	}
	c.data[recordID] = struct{}{}
	c.order = append(c.order, recordID)
	return "db", false
}

func (c *Cache) Set(recordID string) {
	c.lock.Lock()
	defer c.lock.Unlock()

	if _, exists := c.data[recordID]; exists {
		c.moveToEnd(recordID)
		return
	}
	if len(c.data) >= c.cacheSize {
		oldest := c.order[0]
		c.order = c.order[1:]
		delete(c.data, oldest)
	}
	c.data[recordID] = struct{}{}
	c.order = append(c.order, recordID)
}

func (c *Cache) moveToEnd(recordID string) {
	for i, id := range c.order {
		if id == recordID {
			c.order = append(c.order[:i], c.order[i+1:]...)
			break
		}
	}
	c.order = append(c.order, recordID)
}

// sampleLogNormal draws a duration from a log‑normal distribution
// with mean exp(mu + sigma^2/2) = dbMeanMs and log‑stddev sigma.
func (c *Cache) sampleLogNormal() time.Duration {
	// Compute μ so that E[exp(N(μ,σ²))] = dbMeanMs
	mu := math.Log(c.dbMeanMs) - 0.5*c.dbSigma*c.dbSigma
	// Draw a standard normal, scale by σ, shift by μ, then exponentiate
	sampleMs := math.Exp(rand.NormFloat64()*c.dbSigma + mu)
	return time.Duration(sampleMs * float64(time.Millisecond))
}

// burnTargetCPU does small chunks of work and yields, so other goroutines
// can run under GOMAXPROCS=1.
func burnTargetCPU() {
	deadline := time.Now().Add(perRequestCPUDuration)
	for time.Now().Before(deadline) {
		for i := 0; i < 1000; i++ {
			_ = math.Sqrt(float64(i))
		}
		// runtime.Gosched()  // optional
	}
}

func main() {
	gin.SetMode(gin.ReleaseMode)

	// Cache size
	cacheSize, err := strconv.Atoi(getEnv("CACHE_SIZE", "100"))
	if err != nil {
		cacheSize = 100
	}

	// Mean DB latency (ms)
	dbLatencyMs, err := strconv.Atoi(getEnv("DB_LATENCY_MS", "100"))
	if err != nil {
		dbLatencyMs = 100
	}

	// Log‑normal sigma
	sigmaStr := getEnv("DB_LATENCY_SIGMA", "0.5")
	dbSigma, err := strconv.ParseFloat(sigmaStr, 64)
	if err != nil {
		dbSigma = 0.5
	}

	cache := NewCache(cacheSize, time.Duration(dbLatencyMs)*time.Millisecond, dbSigma)

	r := gin.Default()
	r.GET("/getRecord", func(c *gin.Context) {
		recordID := c.Query("record_id")
		source, _ := cache.Get(recordID)
		burnTargetCPU()
		c.JSON(200, gin.H{"source": source, "record_id": recordID})
	})
	r.POST("/setRecord", func(c *gin.Context) {
		recordID := c.Query("record_id")
		cache.Set(recordID)
		c.JSON(200, gin.H{"status": "ok", "record_id": recordID})
	})
	r.Run(":8080")
}

func getEnv(key, fallback string) string {
	if val, exists := os.LookupEnv(key); exists {
		return val
	}
	return fallback
}
