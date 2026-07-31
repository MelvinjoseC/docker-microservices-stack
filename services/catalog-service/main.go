package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type Product struct {
	ID    string  `bson:"_id,omitempty" json:"id"`
	Name  string  `bson:"name" json:"name"`
	Price float64 `bson:"price" json:"price"`
	Stock int     `bson:"stock" json:"stock"`
}

var (
	client         *mongo.Client
	productCol     *mongo.Collection
	isMongoConnect = false
)

func initMongoDB() {
	mongoURI := os.Getenv("MONGO_URI")
	if mongoURI == "" {
		mongoURI = "mongodb://devuser:devpassword@mongodb:27017/catalog_db?authSource=admin"
	}

	var err error
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	// Retry connection
	for i := 0; i < 5; i++ {
		log.Printf("Connecting to MongoDB (attempt %d/5)...", i+1)
		client, err = mongo.Connect(ctx, options.Client().ApplyURI(mongoURI))
		if err == nil {
			err = client.Ping(ctx, nil)
			if err == nil {
				isMongoConnect = true
				log.Println("Successfully connected to MongoDB")
				break
			}
		}
		log.Printf("MongoDB connection error: %v, retrying in 5 seconds...", err)
		time.Sleep(5 * time.Second)
	}

	if !isMongoConnect {
		log.Println("Warning: Failed to connect to MongoDB. Service starting in degraded state.")
		return
	}

	productCol = client.Database("catalog_db").Collection("products")

	// Seed catalog if empty
	count, err := productCol.CountDocuments(context.Background(), bson.M{})
	if err != nil {
		log.Printf("Failed to count catalog documents: %v", err)
		return
	}

	if count == 0 {
		initialProducts := []interface{}{
			Product{ID: "p1", Name: "Developer Laptop", Price: 1299.99, Stock: 50},
			Product{ID: "p2", Name: "Mechanical Keyboard", Price: 89.99, Stock: 150},
			Product{ID: "p3", Name: "Ergonomic Chair", Price: 349.99, Stock: 20},
		}
		_, err := productCol.InsertMany(context.Background(), initialProducts)
		if err != nil {
			log.Printf("Failed to seed product database: %v", err)
		} else {
			log.Println("Seeded initial product catalog to MongoDB")
		}
	}
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	initMongoDB()

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

	// Metrics endpoint
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// Health check
	r.GET("/health", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status":   "degraded",
				"database": "disconnected",
				"service":  "catalog-service",
			})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"status":   "healthy",
			"database": "connected",
			"service":  "catalog-service",
		})
	})

	// Get all products
	r.GET("/api/products", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		cursor, err := productCol.Find(ctx, bson.M{})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		defer cursor.Close(ctx)

		var results []Product
		if err := cursor.All(ctx, &results); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, results)
	})

	// Add new product
	r.POST("/api/products", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		var newProduct Product
		if err := c.ShouldBindJSON(&newProduct); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		// Generate dynamic ID based on timestamp for uniqueness
		newProduct.ID = fmt.Sprintf("p%d", time.Now().UnixNano())

		_, err := productCol.InsertOne(ctx, newProduct)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusCreated, newProduct)
	})

	r.Run(":" + port)
}
