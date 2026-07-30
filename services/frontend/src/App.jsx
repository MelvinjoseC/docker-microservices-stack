import React, { useState, useEffect } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState('catalog');
  const [users, setUsers] = useState([]);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [events, setEvents] = useState([
    { id: 1, time: new Date().toLocaleTimeString(), type: 'info', message: 'System initiated. Connecting to services...' }
  ]);

  // Form states
  const [newUserName, setNewUserName] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [orderQuantity, setOrderQuantity] = useState(1);

  // Health states
  const [health, setHealth] = useState({
    gateway: 'checking',
    users: 'checking',
    catalog: 'checking',
    orders: 'checking'
  });

  const addEvent = (message, type = 'info') => {
    setEvents(prev => [
      { id: Date.now(), time: new Date().toLocaleTimeString(), type, message },
      ...prev
    ]);
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) setHealth(prev => ({ ...prev, gateway: 'healthy' }));
      else setHealth(prev => ({ ...prev, gateway: 'unhealthy' }));
    } catch {
      setHealth(prev => ({ ...prev, gateway: 'unhealthy' }));
    }

    const checkService = async (url, key) => {
      try {
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'healthy') {
            setHealth(prev => ({ ...prev, [key]: 'healthy' }));
          } else {
            setHealth(prev => ({ ...prev, [key]: 'degraded' }));
          }
        } else {
          setHealth(prev => ({ ...prev, [key]: 'unhealthy' }));
        }
      } catch {
        setHealth(prev => ({ ...prev, [key]: 'unhealthy' }));
      }
    };

    checkService('/api/users/health', 'users');
    checkService('/api/products/health', 'catalog');
    checkService('/api/orders/health', 'orders');
  };

  const fetchData = async () => {
    // Fetch products
    try {
      const res = await fetch('/api/products');
      if (res.ok) {
        const data = await res.json();
        setProducts(data);
      }
    } catch (e) {
      console.error("Error fetching products:", e);
    }

    // Fetch users
    try {
      const res = await fetch('/api/users');
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
        if (data.length > 0 && !selectedUserId) {
          setSelectedUserId(data[0].id.toString());
        }
      }
    } catch (e) {
      console.error("Error fetching users:", e);
    }

    // Fetch orders
    try {
      const res = await fetch('/api/orders');
      if (res.ok) {
        const data = await res.json();
        setOrders(data);
      }
    } catch (e) {
      console.error("Error fetching orders:", e);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchData();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUserName || !newUserEmail) return;

    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newUserName, email: newUserEmail })
      });

      if (res.ok) {
        const user = await res.json();
        addEvent(`Created user: ${user.name} (${user.email})`, 'success');
        setNewUserName('');
        setNewUserEmail('');
        fetchData();
      } else {
        const err = await res.json();
        addEvent(`Failed to create user: ${err.error || 'Unknown error'}`, 'error');
      }
    } catch (e) {
      addEvent(`Failed to connect to User service: ${e.message}`, 'error');
    }
  };

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (!selectedUserId || !selectedProductId || orderQuantity < 1) return;

    const product = products.find(p => p.id.toString() === selectedProductId.toString());
    if (!product) return;

    const orderData = {
      user_id: parseInt(selectedUserId),
      items: [
        {
          product_id: product.id,
          quantity: parseInt(orderQuantity),
          price: product.price
        }
      ]
    };

    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
      });

      if (res.ok) {
        const order = await res.json();
        addEvent(`Order #${order.id} placed successfully!`, 'success');
        addEvent(`Event 'order_created' published to RabbitMQ exchange`, 'warn');
        
        // Simulate async background notification consumption log on the UI
        setTimeout(() => {
          addEvent(`Notification Service consumed event. Sending notification to User #${order.user_id}...`, 'info');
        }, 1200);
        setTimeout(() => {
          addEvent(`Notification sent successfully via email stub!`, 'success');
        }, 2500);

        fetchData();
      } else {
        addEvent(`Failed to place order`, 'error');
      }
    } catch (e) {
      addEvent(`Failed to connect to Order service: ${e.message}`, 'error');
    }
  };

  return (
    <div className="app">
      <header>
        <div className="logo">
          <span className="logo-icon">🐳</span>
          <h1>DevOps Stack Dashboard</h1>
        </div>
        <div className="system-status">
          <div className="status-indicator">
            <span className={`dot ${health.gateway === 'healthy' ? 'green' : 'red'}`}></span>
            Gateway
          </div>
          <div className="status-indicator">
            <span className={`dot ${health.users === 'healthy' ? 'green' : health.users === 'degraded' ? 'yellow' : 'red'}`}></span>
            User Service
          </div>
          <div className="status-indicator">
            <span className={`dot ${health.catalog === 'healthy' ? 'green' : health.catalog === 'degraded' ? 'yellow' : 'red'}`}></span>
            Catalog Service
          </div>
          <div className="status-indicator">
            <span className={`dot ${health.orders === 'healthy' ? 'green' : health.orders === 'degraded' ? 'yellow' : 'red'}`}></span>
            Order Service
          </div>
        </div>
      </header>

      <div className="dashboard-grid">
        <div className="main-content">
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
            <button 
              className={`btn ${activeTab === 'catalog' ? '' : 'btn-secondary'}`}
              onClick={() => { setActiveTab('catalog'); fetchData(); }}
              style={{ width: 'auto' }}
            >
              📦 Product Catalog
            </button>
            <button 
              className={`btn ${activeTab === 'orders' ? '' : 'btn-secondary'}`}
              onClick={() => { setActiveTab('orders'); fetchData(); }}
              style={{ width: 'auto' }}
            >
              🛒 Orders Registry
            </button>
            <button 
              className={`btn ${activeTab === 'users' ? '' : 'btn-secondary'}`}
              onClick={() => { setActiveTab('users'); fetchData(); }}
              style={{ width: 'auto' }}
            >
              👥 Manage Users
            </button>
          </div>

          {activeTab === 'catalog' && (
            <div className="panel">
              <h2>Product Catalog ({products.length})</h2>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Product Name</th>
                    <th>Price</th>
                    <th>Stock status</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id}>
                      <td><code>{p.id}</code></td>
                      <td style={{ fontWeight: '600' }}>{p.name}</td>
                      <td>${p.price.toFixed(2)}</td>
                      <td>
                        <span className={`badge ${p.stock > 0 ? 'completed' : 'failed'}`}>
                          {p.stock > 0 ? `${p.stock} in stock` : 'out of stock'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {products.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
                        No products available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'orders' && (
            <div className="panel">
              <h2>Orders List ({orders.length})</h2>
              <table>
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>User ID</th>
                    <th>Total Amount</th>
                    <th>Status</th>
                    <th>Items Count</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(o => (
                    <tr key={o.id}>
                      <td><code>#{o.id}</code></td>
                      <td>User #{o.user_id}</td>
                      <td style={{ fontWeight: '600', color: '#00f2fe' }}>${o.total_amount.toFixed(2)}</td>
                      <td>
                        <span className={`badge ${o.status === 'COMPLETED' ? 'completed' : 'pending'}`}>
                          {o.status}
                        </span>
                      </td>
                      <td>{o.items ? o.items.length : 1} items</td>
                    </tr>
                  ))}
                  {orders.length === 0 && (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
                        No orders recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="panel">
              <h2>Registered Users ({users.length})</h2>
              <table>
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Full Name</th>
                    <th>Email Address</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td><code>{u.id}</code></td>
                      <td style={{ fontWeight: '600' }}>{u.name}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`badge ${u.role === 'admin' ? 'completed' : 'pending'}`}>
                          {u.role}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
                        No users registered.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="sidebar" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Operations Panel */}
          <div className="panel">
            <h2>Quick Actions</h2>
            
            <form onSubmit={handlePlaceOrder} style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '0.95rem', color: '#4facfe', margin: '0 0 1rem 0' }}>🛒 Place Demo Order</h3>
              <div className="form-group">
                <label>Select Customer</label>
                <select value={selectedUserId} onChange={e => setSelectedUserId(e.target.value)}>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>{u.name} (ID: {u.id})</option>
                  ))}
                  {users.length === 0 && <option value="">No customers available</option>}
                </select>
              </div>
              <div className="form-group">
                <label>Select Product</label>
                <select value={selectedProductId} onChange={e => {
                  setSelectedProductId(e.target.value);
                }}>
                  <option value="">-- Choose Product --</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name} - ${p.price}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input 
                  type="number" 
                  min="1" 
                  value={orderQuantity} 
                  onChange={e => setOrderQuantity(e.target.value)} 
                />
              </div>
              <button className="btn" type="submit" disabled={!selectedProductId}>
                Purchase Item
              </button>
            </form>

            <form onSubmit={handleCreateUser}>
              <h3 style={{ fontSize: '0.95rem', color: '#4facfe', margin: '0 0 1rem 0' }}>👥 Create New User</h3>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  placeholder="John Doe" 
                  value={newUserName} 
                  onChange={e => setNewUserName(e.target.value)} 
                  required
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  placeholder="john@example.com" 
                  value={newUserEmail} 
                  onChange={e => setNewUserEmail(e.target.value)} 
                  required
                />
              </div>
              <button className="btn btn-secondary" type="submit">
                Register Account
              </button>
            </form>
          </div>

          {/* Event Stream */}
          <div className="panel">
            <h2>System Activity Logs</h2>
            <div className="logs-list">
              {events.map(ev => (
                <div key={ev.id} className={`log-item ${ev.type === 'error' ? 'error' : ev.type === 'success' ? '' : 'warn'}`}>
                  <div className="log-time">{ev.time}</div>
                  <div className="log-msg">{ev.message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
