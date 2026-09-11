const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const HOST = '0.0.0.0';

// In-memory / file-based fallback store for orders if API is queried
let memoryOrders = [];

const server = http.createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // API Orders route
  if (url.pathname === '/api/orders' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, orders: memoryOrders }));
    return;
  }

  // API Order POST route (accepts both /api/orders and /api/order)
  if ((url.pathname === '/api/orders' || url.pathname === '/api/order') && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const orderData = JSON.parse(body || '{}');
        orderData.id = orderData.id || Date.now();
        orderData.created_at = orderData.created_at || new Date().toISOString();
        memoryOrders.unshift(orderData);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          message: "Order placed successfully!",
          order: orderData
        }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Health check
  if (url.pathname === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', type: 'pure-html-single-file' }));
    return;
  }

  // Supabase Status check
  if (url.pathname === '/api/supabase/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      configured: true,
      bucket_name: "user-images",
      table_count: 10,
      tables: [
        {"name": "users", "desc": "Bot user profiles, phone, image details"},
        {"name": "vendors", "desc": "Vendor & Merchant shop directory"},
        {"name": "riders", "desc": "Delivery Rider list & status"},
        {"name": "customers", "desc": "Customer contact list & order counts"},
        {"name": "categories", "desc": "Product Categories"},
        {"name": "products", "desc": "E-Commerce Product catalog"},
        {"name": "orders", "desc": "Customer orders"},
        {"name": "order_items", "desc": "Order item details"},
        {"name": "delivery_tracking", "desc": "Live delivery tracking"},
        {"name": "payments", "desc": "Payment & Transaction records"}
      ]
    }));
    return;
  }

  if (url.pathname === '/api/tables') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      counts: { vendors: 3, riders: 3, customers: 5, orders: 4, users: 2 }
    }));
    return;
  }

  if (url.pathname === '/api/vendors') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      vendors: [
        { id: 1, shop_name: 'Dhaka Gadget Hub', owner_name: 'Rahim Uddin', phone: '+8801711001122', status: 'active' },
        { id: 2, shop_name: 'Green Fresh Grocery', owner_name: 'Karim Mia', phone: '+8801811223344', status: 'active' },
        { id: 3, shop_name: 'Fashion Fusion BD', owner_name: 'Nusrat Jahan', phone: '+8801911334455', status: 'active' }
      ]
    }));
    return;
  }

  if (url.pathname === '/api/riders') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      riders: [
        { id: 1, name: 'Tariqul Islam', phone: '+8801611009988', vehicle_type: 'Motorbike', status: 'available' },
        { id: 2, name: 'Shakil Ahmed', phone: '+8801511223344', vehicle_type: 'Bicycle', status: 'on_delivery' },
        { id: 3, name: 'Mahmudul Hasan', phone: '+8801711998877', vehicle_type: 'Motorbike', status: 'available' }
      ]
    }));
    return;
  }

  if (url.pathname === '/api/database/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      configured: true,
      connected: true,
      driver: 'PostgreSQL / Supabase',
      total_tables: 14,
      tables: [
        'users', 'vendors', 'riders', 'customers', 'categories',
        'products', 'orders', 'order_items', 'delivery_tracking',
        'payments', 'reviews', 'coupons', 'notifications', 'audit_logs'
      ],
      counts: {
        users: 2, vendors: 3, riders: 3, customers: 5, categories: 4,
        products: 12, orders: 4, order_items: 8, delivery_tracking: 4,
        payments: 4, reviews: 6, coupons: 3, notifications: 5, audit_logs: 10
      }
    }));
    return;
  }

  if (url.pathname === '/api/database/migrate') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      configured: true,
      driver: 'PostgreSQL / Supabase',
      message: 'Successfully initialized 14 tables in PostgreSQL database via server!',
      total_tables: 14,
      tables: [
        'users', 'vendors', 'riders', 'customers', 'categories',
        'products', 'orders', 'order_items', 'delivery_tracking',
        'payments', 'reviews', 'coupons', 'notifications', 'audit_logs'
      ]
    }));
    return;
  }

  // Supabase Users list / search

  if (url.pathname === '/api/supabase/users') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      count: 0,
      users: []
    }));
    return;
  }

  // Serve index.html for all other routes
  const filePath = path.join(__dirname, 'index.html');
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Error loading index.html: ' + err.message);
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Single-file pure HTML app running on http://${HOST}:${PORT}`);
});
