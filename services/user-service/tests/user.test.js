process.env.NODE_ENV = 'test';

const request = require('supertest');
const { app, User } = require('../src/index');

describe('User Service Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Health Checks & Monitoring', () => {
    it('should return degraded if database is not connected', async () => {
      const res = await request(app).get('/health');
      expect([200, 503]).toContain(res.statusCode);
      expect(res.body).toHaveProperty('service', 'user-service');
    });

    it('should respond to /api/users/health path alias', async () => {
      const res = await request(app).get('/api/users/health');
      expect([200, 503]).toContain(res.statusCode);
      expect(res.body).toHaveProperty('service', 'user-service');
    });

    it('should expose Prometheus metrics on /metrics', async () => {
      const res = await request(app).get('/metrics');
      expect(res.statusCode).toBe(200);
      expect(res.text).toContain('user_service_http_requests_total');
    });

    it('should propagate correlation IDs in response headers', async () => {
      const testTraceId = 'trace-abc-12345';
      const res = await request(app)
        .get('/metrics')
        .set('X-Correlation-ID', testTraceId);
      expect(res.headers['x-correlation-id']).toBe(testTraceId);
    });
  });

  describe('User API Validation & Endpoints', () => {
    it('should reject user creation when required fields are missing', async () => {
      const res = await request(app)
        .post('/api/users')
        .send({ name: 'Incomplete User' });

      expect(res.statusCode).toBe(400);
      expect(res.body.error).toContain('Name and email are required');
    });

    it('should reject invalid email format', async () => {
      const res = await request(app)
        .post('/api/users')
        .send({ name: 'Valid Name', email: 'not-an-email' });

      expect(res.statusCode).toBe(400);
      expect(res.body.error).toContain('Invalid email address format');
    });

    it('should fetch user list with pagination params', async () => {
      jest.spyOn(User, 'findAll').mockResolvedValueOnce([
        { id: 1, name: 'Alice Smith', email: 'alice@example.com', role: 'admin' },
        { id: 2, name: 'Bob Jones', email: 'bob@example.com', role: 'user' }
      ]);

      const res = await request(app)
        .get('/api/users?limit=10&offset=0');

      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(2);
    });

    it('should return 404 when user ID does not exist', async () => {
      jest.spyOn(User, 'findByPk').mockResolvedValueOnce(null);

      const res = await request(app).get('/api/users/9999');
      expect(res.statusCode).toBe(404);
      expect(res.body.error).toBe('User not found');
    });
  });
});
