const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Mock DB for boilerplate testing
const users = [
  { id: 1, name: 'Alice Smith', email: 'alice@example.com', role: 'admin' },
  { id: 2, name: 'Bob Jones', email: 'bob@example.com', role: 'user' }
];

// Health Check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'user-service' });
});

// API Routes
app.get('/api/users', (req, res) => {
  res.json(users);
});

app.post('/api/users', (req, res) => {
  const { name, email, role } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required' });
  }
  const newUser = { id: users.length + 1, name, email, role: role || 'user' };
  users.push(newUser);
  res.status(201).json(newUser);
});

app.listen(PORT, () => {
  console.log(`User Service running on port ${PORT}`);
});
