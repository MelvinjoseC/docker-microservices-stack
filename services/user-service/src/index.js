const express = require('express');
const cors = require('cors');
const { Sequelize, DataTypes } = require('sequelize');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Database connection
const dbHost = process.env.DB_HOST || 'postgres';
const dbPort = process.env.DB_PORT || 5432;
const dbUser = process.env.DB_USER || 'devuser';
const dbPassword = process.env.DB_PASSWORD || 'devpassword';
const dbName = process.env.DB_NAME || 'microservices_db';

const sequelize = new Sequelize(dbName, dbUser, dbPassword, {
  host: dbHost,
  port: dbPort,
  dialect: 'postgres',
  logging: false,
  pool: {
    max: 5,
    min: 0,
    acquire: 30000,
    idle: 10000
  }
});

// Define User Model
const User = sequelize.define('User', {
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      isEmail: true
    }
  },
  role: {
    type: DataTypes.STRING,
    defaultValue: 'user'
  }
}, {
  timestamps: true
});

// Database Sync and Setup
let isDbConnected = false;
async function connectDb(retries = 5, delay = 5000) {
  for (let i = 0; i < retries; i++) {
    try {
      await sequelize.authenticate();
      console.log('PostgreSQL database connected successfully.');
      await sequelize.sync({ alter: true });
      console.log('Database schemas synchronized.');
      isDbConnected = true;
      
      // Seed initial users if empty
      const count = await User.count();
      if (count === 0) {
        await User.bulkCreate([
          { name: 'Alice Smith', email: 'alice@example.com', role: 'admin' },
          { name: 'Bob Jones', email: 'bob@example.com', role: 'user' }
        ]);
        console.log('Seeded default users.');
      }
      return;
    } catch (error) {
      console.error(`Database connection failed (attempt ${i + 1}/${retries}):`, error.message);
      if (i < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  console.error('Could not connect to database after retries. Starting server in degraded state.');
}

// Health Check
app.get('/health', async (req, res) => {
  if (!isDbConnected) {
    return res.status(503).json({ status: 'degraded', database: 'disconnected', service: 'user-service' });
  }
  try {
    await sequelize.authenticate();
    res.status(200).json({ status: 'healthy', database: 'connected', service: 'user-service' });
  } catch (error) {
    res.status(500).json({ status: 'unhealthy', error: error.message, service: 'user-service' });
  }
});

// API Routes
app.get('/api/users', async (req, res) => {
  try {
    const users = await User.findAll();
    res.json(users);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/users', async (req, res) => {
  const { name, email, role } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required' });
  }
  try {
    const newUser = await User.create({ name, email, role: role || 'user' });
    res.status(201).json(newUser);
  } catch (error) {
    if (error.name === 'SequelizeUniqueConstraintError') {
      return res.status(409).json({ error: 'Email already exists' });
    }
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, async () => {
  console.log(`User Service running on port ${PORT}`);
  await connectDb();
});
