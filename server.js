const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const HOST = '0.0.0.0';

let TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '';
let TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || '';
let ADMIN_TELEGRAM_ID = process.env.ADMIN_TELEGRAM_ID || '';
let ADMIN_PIN = process.env.ADMIN_PIN || '1234';

// In-memory product catalog (Experiment mode, no database)
let memoryProducts = [
  {
    id: "prod-1",
    name: "Wireless Noise-Cancelling Earbuds",
    category: "Audio",
    price: 49.99,
    stock: 25,
    image: "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&auto=format&fit=crop&q=80",
    badge: "Best Seller",
    description: "Active noise cancelling with 28-hour battery life and waterproof build."
  },
  {
    id: "prod-2",
    name: "Vintage Mechanical Keyboard RGB",
    category: "Workplace",
    price: 89.50,
    stock: 14,
    image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=300&auto=format&fit=crop&q=80",
    badge: "Popular",
    description: "Custom mechanical switches with per-key RGB backlighting and aluminum body."
  },
  {
    id: "prod-3",
    name: "Smart Fitness Tracker Band",
    category: "Wearables",
    price: 34.99,
    stock: 30,
    image: "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=300&auto=format&fit=crop&q=80",
    badge: "New Arrival",
    description: "24/7 heart rate monitor, sleep analysis, SpO2 sensor and 14-day battery."
  },
  {
    id: "prod-4",
    name: "Ultra-light Commuter Backpack",
    category: "Accessories",
    price: 59.00,
    stock: 18,
    image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&auto=format&fit=crop&q=80",
    badge: "Waterproof",
    description: "Ergonomic waterproof backpack with padded 16-inch laptop compartment."
  }
];

// In-memory experiment store for orders (No database)
let memoryOrders = [
  {
    id: 1001,
    order_number: "ORD-2026-001",
    customer_name: "Alex Morgan",
    phone_number: "+1 (555) 019-2834",
    product_name: "Wireless Noise-Cancelling Earbuds",
    quantity: 1,
    unit_price: 49.99,
    total_price: 49.99,
    status: "delivered",
    notes: "Please leave package at front reception.",
    source: "Telegram Chat Bot (/order)",
    telegram_user_id: "78239102",
    telegram_username: "alex_morgan",
    created_at: new Date(Date.now() - 3600000 * 24).toISOString()
  },
  {
    id: 1002,
    order_number: "ORD-2026-002",
    customer_name: "Sarah Chen",
    phone_number: "+1 (555) 014-9921",
    product_name: "Vintage Mechanical Keyboard RGB",
    quantity: 2,
    unit_price: 89.50,
    total_price: 179.00,
    status: "processing",
    notes: "Gift packaging requested with blue ribbon.",
    source: "Telegram Chat Bot (/order)",
    telegram_user_id: "89123041",
    telegram_username: "sarah_c",
    created_at: new Date(Date.now() - 3600000 * 4).toISOString()
  },
  {
    id: 1003,
    order_number: "ORD-2026-003",
    customer_name: "Tariqul Islam",
    phone_number: "+880 1711-223344",
    product_name: "Smart Fitness Tracker Band",
    quantity: 1,
    unit_price: 34.99,
    total_price: 34.99,
    status: "pending",
    notes: "Call before delivery.",
    source: "Telegram Chat Bot (/order)",
    telegram_user_id: "99482103",
    telegram_username: "tariq_bd",
    created_at: new Date(Date.now() - 3600000 * 1).toISOString()
  }
];

function formatTelegramAlert(order) {
  const usernameLine = order.telegram_username ? `\n👤 *Telegram User:* @${order.telegram_username}` : "";
  const userIdLine = order.telegram_user_id ? ` (ID: \`${order.telegram_user_id}\`)` : "";
  const notesLine = order.notes ? `\n📝 *Notes:* _${order.notes}_` : "";
  const total = Number(order.total_price || 0).toFixed(2);
  const qty = order.quantity || 1;

  return (
    "🔔 *NEW ORDER ALERT (ADMIN ONLY)*\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n" +
    `🔖 *Order Ref:* \`${order.order_number || 'N/A'}\`\n` +
    `👤 *Customer:* *${order.customer_name || 'N/A'}*\n` +
    `📞 *Phone:* \`${order.phone_number || 'N/A'}\`\n` +
    `📦 *Product:* *${order.product_name || 'N/A'}*\n` +
    `🔢 *Quantity:* ${qty} unit${qty > 1 ? 's' : ''}\n` +
    `💰 *Total Amount:* $${total}\n` +
    `📍 *Channel:* ${order.source || 'Telegram Chat Bot'}` +
    `${usernameLine}${userIdLine}` +
    `${notesLine}\n` +
    `🕒 *Time:* ${new Date().toISOString()}\n` +
    "━━━━━━━━━━━━━━━━━━━━━━\n" +
    "⚡ _Manage in Admin Mini App: /admin_"
  );
}

function sendTelegramAlert(order, customToken, customChatId) {
  return new Promise((resolve) => {
    const token = customToken || TELEGRAM_BOT_TOKEN;
    const targetChat = customChatId || TELEGRAM_CHAT_ID || ADMIN_TELEGRAM_ID;
    const alertText = formatTelegramAlert(order);

    if (!token || !targetChat) {
      return resolve({
        success: false,
        error: "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.",
        simulated: true,
        preview_message: alertText
      });
    }

    const payload = JSON.stringify({
      chat_id: targetChat,
      text: alertText,
      parse_mode: "Markdown"
    });

    const options = {
      hostname: 'api.telegram.org',
      port: 443,
      path: `/bot${token}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: 10000
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.ok) {
            resolve({ success: true, result: json });
          } else {
            resolve({ success: false, error: json.description || 'Telegram API Error' });
          }
        } catch (e) {
          resolve({ success: false, error: e.message });
        }
      });
    });

    req.on('error', (e) => {
      resolve({ success: false, error: e.message, preview_message: alertText });
    });

    req.write(payload);
    req.end();
  });
}

function sendTelegramCustomMessage(chatId, text, replyMarkup = null, customToken = null) {
  return new Promise((resolve) => {
    const token = customToken || TELEGRAM_BOT_TOKEN;
    if (!token || !chatId) {
      return resolve({ success: false, error: "Bot token or chat ID missing." });
    }

    const bodyObj = {
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown"
    };
    if (replyMarkup) {
      bodyObj.reply_markup = replyMarkup;
    }

    const payload = JSON.stringify(bodyObj);
    const options = {
      hostname: 'api.telegram.org',
      port: 443,
      path: `/bot${token}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: 10000
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve({ success: Boolean(json.ok), result: json });
        } catch (e) {
          resolve({ success: false, error: e.message });
        }
      });
    });

    req.on('error', (e) => {
      resolve({ success: false, error: e.message });
    });

    req.write(payload);
    req.end();
  });
}

const server = http.createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Pin');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  // Health check
  if (url.pathname === '/api/health' || url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      system: 'Telegram Bot & Admin-Only Mini App (In-Memory Experiment Mode)',
      database: 'none (in-memory experiment)',
      timestamp: new Date().toISOString(),
      has_bot_token: Boolean(TELEGRAM_BOT_TOKEN),
      has_chat_id: Boolean(TELEGRAM_CHAT_ID),
      has_admin_id: Boolean(ADMIN_TELEGRAM_ID),
      orders_count: memoryOrders.length,
      products_count: memoryProducts.length
    }));
    return;
  }

  // Admin Verification Endpoint POST /api/admin/verify
  if (url.pathname === '/api/admin/verify' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const pin = String(payload.pin || '').trim();
        const tgUserId = String(payload.telegram_user_id || '').trim();

        let isAdmin = false;
        let matchReason = '';

        // 1. Check PIN match
        if (pin && pin === String(ADMIN_PIN).trim()) {
          isAdmin = true;
          matchReason = 'Admin Security PIN verified';
        }

        // 2. Check Telegram User ID match with configured admin ID or chat ID
        if (!isAdmin && tgUserId) {
          if (ADMIN_TELEGRAM_ID && tgUserId === String(ADMIN_TELEGRAM_ID).trim()) {
            isAdmin = true;
            matchReason = `Telegram User ID matched ADMIN_TELEGRAM_ID (${tgUserId})`;
          } else if (TELEGRAM_CHAT_ID && tgUserId === String(TELEGRAM_CHAT_ID).trim()) {
            isAdmin = true;
            matchReason = `Telegram User ID matched configured TELEGRAM_CHAT_ID (${tgUserId})`;
          }
        }

        if (isAdmin) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: true,
            isAdmin: true,
            message: matchReason || 'Admin authentication successful',
            admin_id: tgUserId || 'admin_session'
          }));
        } else {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: false,
            isAdmin: false,
            error: 'Access Denied. Mini App is restricted to Admin only. Enter valid Admin PIN or launch from Admin Telegram Account.'
          }));
        }
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Admin Config GET & POST /api/admin/config
  if (url.pathname === '/api/admin/config' || url.pathname === '/api/config') {
    if (req.method === 'POST') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const data = JSON.parse(body || '{}');
          if (data.bot_token !== undefined) TELEGRAM_BOT_TOKEN = data.bot_token.trim();
          if (data.chat_id !== undefined) TELEGRAM_CHAT_ID = data.chat_id.trim();
          if (data.admin_telegram_id !== undefined) ADMIN_TELEGRAM_ID = data.admin_telegram_id.trim();
          if (data.admin_pin !== undefined && data.admin_pin.trim()) ADMIN_PIN = data.admin_pin.trim();

          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: true,
            message: 'Admin & Bot configuration updated in memory',
            has_bot_token: Boolean(TELEGRAM_BOT_TOKEN),
            has_chat_id: Boolean(TELEGRAM_CHAT_ID),
            admin_telegram_id: ADMIN_TELEGRAM_ID
          }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: e.message }));
        }
      });
      return;
    }

    // GET
    let tokenMasked = '';
    if (TELEGRAM_BOT_TOKEN) {
      const parts = TELEGRAM_BOT_TOKEN.split(':');
      tokenMasked = parts.length > 1 ? `${parts[0]}:***` : '***';
    }

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      has_bot_token: Boolean(TELEGRAM_BOT_TOKEN),
      has_chat_id: Boolean(TELEGRAM_CHAT_ID),
      has_admin_id: Boolean(ADMIN_TELEGRAM_ID),
      bot_token_masked: tokenMasked,
      chat_id: TELEGRAM_CHAT_ID,
      admin_telegram_id: ADMIN_TELEGRAM_ID,
      admin_pin_configured: Boolean(ADMIN_PIN),
      database_mode: "In-Memory Experiment (Zero Database Requirement)"
    }));
    return;
  }

  // Products Catalog GET & POST /api/products
  if (url.pathname === '/api/products') {
    if (req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, products: memoryProducts }));
      return;
    }
    if (req.method === 'POST') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const item = JSON.parse(body || '{}');
          const newProd = {
            id: `prod-${Date.now()}`,
            name: item.name || 'New Experiment Item',
            category: item.category || 'General',
            price: parseFloat(item.price || 10.0),
            stock: parseInt(item.stock || 10, 10),
            image: item.image || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300',
            badge: item.badge || 'New',
            description: item.description || ''
          };
          memoryProducts.push(newProd);
          res.writeHead(201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, product: newProd }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: e.message }));
        }
      });
      return;
    }
  }

  // API Orders route (GET, POST, DELETE all)
  if (url.pathname === '/api/orders' || url.pathname === '/api/order') {
    if (req.method === 'GET') {
      const q = (url.searchParams.get('q') || '').toLowerCase().trim();
      const statusFilter = url.searchParams.get('status') || '';

      let results = [...memoryOrders];
      if (statusFilter) {
        results = results.filter(o => o.status === statusFilter);
      }
      if (q) {
        results = results.filter(o =>
          (o.customer_name && o.customer_name.toLowerCase().includes(q)) ||
          (o.phone_number && o.phone_number.includes(q)) ||
          (o.order_number && o.order_number.toLowerCase().includes(q)) ||
          (o.product_name && o.product_name.toLowerCase().includes(q))
        );
      }

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: true,
        orders: results,
        total_count: memoryOrders.length,
        stats: {
          pending: memoryOrders.filter(o => o.status === 'pending').length,
          processing: memoryOrders.filter(o => o.status === 'processing').length,
          delivered: memoryOrders.filter(o => o.status === 'delivered').length,
          cancelled: memoryOrders.filter(o => o.status === 'cancelled').length,
          total_revenue: memoryOrders.reduce((sum, o) => sum + (Number(o.total_price) || 0), 0)
        }
      }));
      return;
    }

    if (req.method === 'POST') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', async () => {
        try {
          const orderData = JSON.parse(body || '{}');
          const count = memoryOrders.length + 1;
          const paddedIndex = String(count).padStart(3, '0');
          const refId = `ORD-EXP-${paddedIndex}`;

          const unitPrice = parseFloat(orderData.unit_price || 0);
          const qty = parseInt(orderData.quantity || 1, 10);
          let totalPrice = parseFloat(orderData.total_price || 0);
          if (totalPrice === 0 && unitPrice > 0) {
            totalPrice = unitPrice * qty;
          }

          const newOrder = {
            id: Date.now(),
            order_number: orderData.order_number || refId,
            customer_name: orderData.customer_name || 'Experiment Customer',
            phone_number: orderData.phone_number || 'N/A',
            product_name: orderData.product_name || 'General Product',
            quantity: qty,
            unit_price: unitPrice,
            total_price: totalPrice,
            status: orderData.status || 'pending',
            notes: orderData.notes || '',
            source: orderData.source || 'Telegram Chat Bot (/order)',
            telegram_user_id: String(orderData.telegram_user_id || ''),
            telegram_username: String(orderData.telegram_username || ''),
            created_at: new Date().toISOString()
          };

          memoryOrders.unshift(newOrder);

          // Dispatch real-time alert to Admin Telegram
          const tgResult = await sendTelegramAlert(newOrder);

          res.writeHead(201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: true,
            message: "Order placed & Admin alert triggered!",
            order: newOrder,
            telegram: tgResult
          }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: e.message }));
        }
      });
      return;
    }

    if (req.method === 'DELETE') {
      memoryOrders = [];
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, message: "All experiment orders cleared from memory." }));
      return;
    }
  }

  // Update order status PATCH /api/order/:id/status or /api/orders/:id/status
  const statusMatch = url.pathname.match(/^\/api\/(?:order|orders)\/(\d+)\/status$/);
  if (statusMatch && req.method === 'PATCH') {
    const orderId = parseInt(statusMatch[1], 10);
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const newStatus = payload.status || 'pending';
        const targetOrder = memoryOrders.find(o => o.id === orderId);
        if (targetOrder) {
          targetOrder.status = newStatus;
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: true,
            message: `Order #${orderId} status updated to ${newStatus}`,
            order: targetOrder
          }));
        } else {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: 'Order not found' }));
        }
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Delete single order DELETE /api/orders/:id
  const deleteMatch = url.pathname.match(/^\/api\/orders\/(\d+)$/);
  if (deleteMatch && req.method === 'DELETE') {
    const orderId = parseInt(deleteMatch[1], 10);
    const initialLen = memoryOrders.length;
    memoryOrders = memoryOrders.filter(o => o.id !== orderId);
    if (memoryOrders.length < initialLen) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, message: `Order #${orderId} deleted` }));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: 'Order not found' }));
    }
    return;
  }

  // Test Telegram alert POST /api/test-telegram
  if (url.pathname === '/api/test-telegram' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const data = JSON.parse(body || '{}');
        const customToken = data.bot_token || TELEGRAM_BOT_TOKEN;
        const customChat = data.chat_id || TELEGRAM_CHAT_ID || ADMIN_TELEGRAM_ID;

        const testOrder = {
          id: 9999,
          order_number: "TEST-ALERT-001",
          customer_name: "Test Customer (Experiment)",
          phone_number: "+1 (555) 019-2834",
          product_name: "Wireless Noise-Cancelling Earbuds",
          quantity: 1,
          unit_price: 49.99,
          total_price: 49.99,
          notes: "Testing Admin Telegram Alert integration.",
          source: "Telegram Chat Bot (/order)",
          telegram_user_id: customChat || "123456789",
          telegram_username: "admin_tester",
          created_at: new Date().toISOString()
        };

        const resResult = await sendTelegramAlert(testOrder, customToken, customChat);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(resResult));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Setup Bot Commands: Only Register Chat Commands for Regular Users, and Send /admin Mini App Card to Admin
  if (url.pathname === '/api/setup-bot-commands' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        const token = payload.bot_token || TELEGRAM_BOT_TOKEN;
        const adminChatId = payload.admin_chat_id || ADMIN_TELEGRAM_ID || TELEGRAM_CHAT_ID;
        const miniAppUrl = payload.web_app_url || `https://${req.headers.host || 'localhost'}`;

        if (!token) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: false,
            error: "TELEGRAM_BOT_TOKEN is not configured. Please enter Bot Token first."
          }));
          return;
        }

        // 1. Register Public Commands for Regular Users (Chat only, NO mini app for regular users)
        const userCommands = [
          { command: "start", description: "👋 Start bot & view store instructions" },
          { command: "menu", description: "🛍️ View products & pricing list in chat" },
          { command: "order", description: "📦 Place an order via chat message" },
          { command: "help", description: "ℹ️ Customer support and ordering guide" },
          { command: "status", description: "📍 Check your Telegram Chat ID" }
        ];

        const cmdReqPayload = JSON.stringify({ commands: userCommands });
        const cmdPromise = new Promise(resolve => {
          const opt = {
            hostname: 'api.telegram.org',
            port: 443,
            path: `/bot${token}/setMyCommands`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(cmdReqPayload) }
          };
          const r = https.request(opt, res => {
            let d = '';
            res.on('data', c => { d += c; });
            res.on('end', () => {
              try { resolve(JSON.parse(d)); } catch (e) { resolve({ ok: false, error: e.message }); }
            });
          });
          r.on('error', e => resolve({ ok: false, error: e.message }));
          r.write(cmdReqPayload);
          r.end();
        });

        // 2. Remove any global Mini App chat menu button so regular users do NOT get the mini app
        const menuRemovePayload = JSON.stringify({ menu_button: { type: "default" } });
        const menuPromise = new Promise(resolve => {
          const opt = {
            hostname: 'api.telegram.org',
            port: 443,
            path: `/bot${token}/setChatMenuButton`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(menuRemovePayload) }
          };
          const r = https.request(opt, res => {
            let d = '';
            res.on('data', c => { d += c; });
            res.on('end', () => {
              try { resolve(JSON.parse(d)); } catch (e) { resolve({ ok: false, error: e.message }); }
            });
          });
          r.on('error', e => resolve({ ok: false, error: e.message }));
          r.write(menuRemovePayload);
          r.end();
        });

        const [cmdResult, menuResult] = await Promise.all([cmdPromise, menuPromise]);

        // 3. If Admin Chat ID is configured, send the Private Admin Mini App Launcher button ONLY to Admin
        let adminCardResult = null;
        if (adminChatId) {
          const adminText = (
            "🔐 *ADMIN CONTROL ACCESS*\n" +
            "━━━━━━━━━━━━━━━━━━━━━━\n" +
            "👑 *Administrator Privileges Verified*\n\n" +
            "The Mini App is now **restricted exclusively for Admin access**.\n" +
            "• Regular users order in chat using `/menu` and `/order`.\n" +
            "• Use the secure button below to launch the **Admin Control Mini App** to manage orders, inventory, and alerts."
          );
          const adminKeyboard = {
            inline_keyboard: [
              [
                { text: "⚡ Launch Admin Mini App (Private)", web_app: { url: miniAppUrl } }
              ],
              [
                { text: "📊 Quick Order Stats", callback_data: "admin_stats" }
              ]
            ]
          };
          adminCardResult = await sendTelegramCustomMessage(adminChatId, adminText, adminKeyboard, token);
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          message: "Bot commands configured! User chat commands set (Mini App removed for users). Admin Mini App card dispatched to Admin.",
          details: {
            userCommandsSet: cmdResult,
            chatMenuRestrictedToDefault: menuResult,
            adminCardSent: adminCardResult
          }
        }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Simulate Telegram Bot Response (For local experiment & preview) POST /api/bot/simulate-message
  if (url.pathname === '/api/bot/simulate-message' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const message = String(payload.message || '').trim().toLowerCase();
        const isAdmin = Boolean(payload.is_admin);
        const userName = payload.user_name || (isAdmin ? "Store Admin" : "Customer");
        const miniAppUrl = `https://${req.headers.host || 'localhost'}`;

        let reply = {};

        if (message === '/admin') {
          if (isAdmin) {
            reply = {
              sender: "Bot",
              type: "admin_card",
              text: `🔐 *Welcome Administrator (${userName})!*\n━━━━━━━━━━━━━━━━━━━━━━\nHere is your private Admin Mini App to review experiment orders, update status, and manage products.`,
              buttons: [
                { text: "⚡ Open Admin Control Mini App", action: "open_admin_app", url: miniAppUrl }
              ]
            };
          } else {
            reply = {
              sender: "Bot",
              type: "error",
              text: `🚫 *Access Denied*\nThe \`/admin\` command is restricted to Store Administrators. If you are an admin, configure your Admin Telegram ID or enter PIN in Admin Portal.`
            };
          }
        } else if (message === '/start') {
          reply = {
            sender: "Bot",
            type: "user_welcome",
            text: `👋 *Welcome to our Store, ${userName}!*\n━━━━━━━━━━━━━━━━━━━━━━\nBrowse products, get pricing, and place your order directly via chat!\n\n💡 *Chat Commands:*\n• \`/menu\` - View our product catalog & prices\n• \`/order\` - Place an order directly in chat\n• \`/help\` - Get support & contact details\n• \`/status\` - Check your Telegram ID\n\n_(Note: Ordering is handled seamlessly in chat. Admin portal is reserved for store admins.)_`,
            buttons: [
              { text: "🛍️ View Catalog (/menu)", action: "send_menu" },
              { text: "📦 Order Item (/order)", action: "send_order" }
            ]
          };
        } else if (message === '/menu' || message === 'menu') {
          const catalogText = memoryProducts.map((p, idx) => 
            `*${idx + 1}. ${p.name}*\n💰 Price: *$${p.price.toFixed(2)}* | Stock: ${p.stock} pcs\n_${p.description}_`
          ).join("\n\n");

          reply = {
            sender: "Bot",
            type: "menu",
            text: `🛍️ *PRODUCT CATALOG (CHAT)*\n━━━━━━━━━━━━━━━━━━━━━━\n${catalogText}\n━━━━━━━━━━━━━━━━━━━━━━\n👉 To order, send: \`/order <Item Number> <Quantity> <Your Phone>\`\n_Example: \`/order 1 1 +8801711223344\`_`
          };
        } else if (message.startsWith('/order')) {
          reply = {
            sender: "Bot",
            type: "order_guide",
            text: `📦 *Place Order via Chat*\nTo place an order, send your product choice, quantity, and delivery phone number.\n\nOur team receives your alert instantly in the Admin Mini App and processes delivery!`
          };
        } else {
          reply = {
            sender: "Bot",
            type: "general",
            text: `🤖 I am the Storefront Bot. Send \`/menu\` to see products or \`/help\` for assistance.`
          };
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, reply }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
    return;
  }

  // Static File Serving (index.html)
  const filePath = path.join(__dirname, 'index.html');
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Error loading index.html');
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Telegram Bot & Admin-Only Mini App running on http://${HOST}:${PORT}`);
});
