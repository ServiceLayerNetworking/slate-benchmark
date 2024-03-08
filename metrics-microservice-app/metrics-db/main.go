package main

import "github.com/gin-gonic/gin"

func main() {
	// gin server that handles GET /dbcall

	r := gin.Default()
	r.GET("/dbcall", DbCall)
	r.Run(":8080")
}

func DbCall(c *gin.Context) {
	// do nothing
	// return 200
	c.JSON(200, gin.H{
		"status": "ok",
	})
}
