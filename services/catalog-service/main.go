package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
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

// Structured JSON Logger Middleware with correlation ID propagation
func jsonLoggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path

		correlationID := c.GetHeader("X-Correlation-ID")
		if correlationID == "" {
			correlationID = c.GetHeader("X-Request-ID")
		}
		if correlationID == "" {
			correlationID = fmt.Sprintf("cat-%d", time.Now().UnixNano())
		}
		c.Header("X-Correlation-ID", correlationID)

		c.Next()

		if path != "/metrics" {
			duration := time.Since(start)
			logEntry := map[string]interface{}{
				"timestamp":      time.Now().UTC().Format(time.RFC3339),
				"correlation_id": correlationID,
				"level":          "info",
				"method":         c.Request.Method,
				"path":           path,
				"status":         c.Writer.Status(),
				"duration_ms":    float64(duration.Microseconds()) / 1000.0,
				"service":        "catalog-service",
			}
			if c.Writer.Status() >= 400 {
				logEntry["level"] = "error"
			}
			jsonBytes, err := json.Marshal(logEntry)
			if err == nil {
				fmt.Println(string(jsonBytes))
			}
		}
	}
}

func setupRouter() *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(jsonLoggerMiddleware())

	// CORS middleware
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With, X-Correlation-ID, X-Request-ID")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Metrics endpoint
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// Health check handler
	healthHandler := func(c *gin.Context) {
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
	}

	r.GET("/health", healthHandler)
	r.GET("/api/products/health", healthHandler)

	// Get all products with optional name filtering
	r.GET("/api/products", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		filter := bson.M{}
		searchQuery := c.Query("search")
		if searchQuery != "" {
			filter["name"] = bson.M{"$regex": searchQuery, "$options": "i"}
		}

		cursor, err := productCol.Find(ctx, filter)
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

		if results == nil {
			results = []Product{}
		}

		c.JSON(http.StatusOK, results)
	})

	// Get product by ID
	r.GET("/api/products/:id", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		id := c.Param("id")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		var product Product
		err := productCol.FindOne(ctx, bson.M{"_id": id}).Decode(&product)
		if err != nil {
			if err == mongo.ErrNoDocuments {
				c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, product)
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

		if newProduct.Name == "" || newProduct.Price < 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid product name or price"})
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if newProduct.ID == "" {
			newProduct.ID = fmt.Sprintf("p%d", time.Now().UnixNano())
		}

		_, err := productCol.InsertOne(ctx, newProduct)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusCreated, newProduct)
	})

	// Update existing product
	r.PUT("/api/products/:id", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		id := c.Param("id")
		var updateData Product
		if err := c.ShouldBindJSON(&updateData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		updateDoc := bson.M{
			"$set": bson.M{
				"name":  updateData.Name,
				"price": updateData.Price,
				"stock": updateData.Stock,
			},
		}

		res, err := productCol.UpdateOne(ctx, bson.M{"_id": id}, updateDoc)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		if res.MatchedCount == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
			return
		}

		updateData.ID = id
		c.JSON(http.StatusOK, updateData)
	})

	// Delete product
	r.DELETE("/api/products/:id", func(c *gin.Context) {
		if !isMongoConnect {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Database not connected"})
			return
		}

		id := c.Param("id")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		res, err := productCol.DeleteOne(ctx, bson.M{"_id": id})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		if res.DeletedCount == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "Product successfully deleted"})
	})

	return r
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	initMongoDB()

	router := setupRouter()

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: router,
	}

	// Initializing the server in a goroutine so that it won't block graceful shutdown handling
	go func() {
		log.Printf("Catalog Service starting on port %s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server startup failed: %s\n", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down Catalog Service...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	if client != nil {
		_ = client.Disconnect(ctx)
		log.Println("MongoDB connection closed cleanly.")
	}

	log.Println("Catalog Service exiting.")
}
