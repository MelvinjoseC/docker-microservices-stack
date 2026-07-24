package main

import (
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

type Product struct {
	ID    string  `json:"id"`
	Name  string  `json:"name"`
	Price float64 `json:"price"`
	Stock int     `json:"stock"`
}

var products = []Product{
	{ID: "p1", Name: "Developer Laptop", Price: 1299.99, Stock: 50},
	{ID: "p2", Name: "Mechanical Keyboard", Price: 89.99, Stock: 150},
	{ID: "p3", Name: "Ergonomic Chair", Price: 349.99, Stock: 20},
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	r := gin.Default()

	// CORS middleware
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Health check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "catalog-service",
		})
	})

	// Get all products
	r.GET("/api/products", func(c *gin.Context) {
		c.JSON(http.StatusOK, products)
	})

	// Add new product
	r.POST("/api/products", func(c *gin.Context) {
		var newProduct Product
		if err := c.ShouldBindJSON(&newProduct); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		newProduct.ID = "p" + string(rune(len(products)+1))
		products = append(products, newProduct)
		c.JSON(http.StatusCreated, newProduct)
	})

	r.Run(":" + port)
}
