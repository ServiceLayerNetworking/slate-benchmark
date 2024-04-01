package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"syscall"
	"time"
)

var wg sync.WaitGroup


func RunCPULoad(cpuPct int, ch chan bool) {
	if cpuPct == 0 {
		return
	}

	runFor := time.Duration(1000*cpuPct) * time.Microsecond
	sleepFor := time.Duration(1000*(100-cpuPct)) * time.Microsecond
	fmt.Printf("Worker sleepFor %s, runFor %s\n", sleepFor.String(), runFor.String())
	runtime.LockOSThread()
	// every milliseconds, run for runMicrosecond microseconds, and sleep for sleepMicrosecond microseconds

startLoop:
	for {
		select {
		case <-ch:
			runtime.UnlockOSThread()
			wg.Done()
			return
		default:
			begin := time.Now()
			for {
				select {
				case <-ch:
					fmt.Printf("Done\n")
					runtime.UnlockOSThread()
					wg.Done()
					return
				default:
					if time.Since(begin) > runFor {
						for {
							select {
							case <-ch:
								fmt.Printf("Done\n")
								runtime.UnlockOSThread()
								wg.Done()
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
	// parse argument for what percentage each cpu should be locked for
	cpuPct := flag.Int("cpu", 50, "percentage of cpu to lock")
	flag.Parse()
	sigs := make(chan os.Signal, 9)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)

	chans := make(map[int]chan bool)
	numCpus := runtime.NumCPU()
	fmt.Printf("Number of CPUs: %d at %d%%\n", numCpus, *cpuPct)

	// lock the cpu for the given percentage
	wg.Add(numCpus)
	for i := 0; i < numCpus; i++ {
		chans[i] = make(chan bool, 1)
		go RunCPULoad(*cpuPct, chans[i])
	}
	// wait for SIGINT
	<-sigs
	fmt.Println("SIGINT received, exiting.")
	// time.Sleep(5 * time.Hour)
	before := time.Now()
	for i := 0; i < numCpus; i++ {
		chans[i] <- true
	}
	waitTimeout(&wg, 1*time.Second)
	fmt.Printf("Time taken: %s\n", time.Since(before).String())
}
func waitTimeout(wg *sync.WaitGroup, timeout time.Duration) bool {
	c := make(chan struct{})
	go func() {
		defer close(c)
		wg.Wait()
	}()
	select {
	case <-c:
		return false // completed normally
	case <-time.After(timeout):
		return true // timed out
	}
}
