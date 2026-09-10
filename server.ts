import express from "express";
import path from "path";
import fs from "fs";
import { execFile } from "child_process";
import { promisify } from "util";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const execFileAsync = promisify(execFile);
const app = express();
const PORT = 3000;

app.use(express.json());

let runtimeBotToken = process.env.TELEGRAM_BOT_TOKEN || "";
let runtimeChatId = process.env.TELEGRAM_CHAT_ID || "";
const appUrl = process.env.APP_URL || "https://ais-dev-ol3fggqvvqo727vfyki4k2-298691348862.asia-southeast1.run.app";

// Helper to format Telegram alert message in Markdown
function formatTelegramAlert(order: any) {
  const sourceBadge = order.is_telegram_webapp ? "📱 Telegram Mini App" : "🌐 Standard Web Browser";
  const userLine = order.telegram_username ? `\n👤 *Telegram User:* @${order.telegram_username}` : "";
  const idLine = order.telegram_user_id ? ` (ID: \`${order.telegram_user_id}\`)` : "";
  const notesLine = order.notes ? `\n📝 *Notes:* _${order.notes}_` : "";
  const total = Number(order.total_price || 0).toFixed(2);
  const qty = order.quantity || 1;

  return (
    `🛒 *NEW ORDER RECEIVED!*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━\n` +
    `🔖 *Order Ref:* \`${order.order_number || "N/A"}\`\n` +
    `👤 *Customer:* ${order.customer_name}\n` +
    `📞 *Phone:* \`${order.phone_number}\`\n` +
    `📦 *Item:* *${order.product_name}*\n` +
    `🔢 *Quantity:* ${qty} pc${Number(qty) > 1 ? "s" : ""}\n` +
    `💰 *Total Amount:* $${total}\n` +
    `🏷️ *Source:* ${sourceBadge}` +
    `${userLine}${idLine}` +
    `${notesLine}\n` +
    `🕒 *Time:* ${new Date().toISOString().replace("T", " ").substring(0, 19)} UTC\n` +
    `━━━━━━━━━━━━━━━━━━━━━━\n` +
    `⚡ _Processed via Telegram E-Commerce System_`
  );
}

// Function to send Telegram message
async function sendTelegramMessage(text: string, customToken?: string, customChat?: string) {
  const token = customToken || runtimeBotToken;
  const chat = customChat || runtimeChatId;

  if (!token || !chat) {
    return {
      success: false,
      isSimulated: true,
      error: "Telegram Bot Token or Chat ID is not configured.",
      previewMessage: text
    };
  }

  try {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chat,
        text: text,
        parse_mode: "Markdown"
      })
    });

    const data = await res.json();
    if (data.ok) {
      return { success: true, result: data };
    } else {
      return { success: false, error: data.description || "Failed to send message via Telegram API", previewMessage: text };
    }
  } catch (err: any) {
    return { success: false, error: err.message, previewMessage: text };
  }
}

// Ensure database table exists via Python database module on start
try {
  execFileAsync("python3", ["database.py", "init"]).catch((err) => {
    console.warn("Python database init warning:", err.message);
  });
} catch (e) {
  console.warn("Could not invoke python3 database.py init:", e);
}

// API Routes
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    has_bot_token: Boolean(runtimeBotToken),
    has_chat_id: Boolean(runtimeChatId),
    app_url: appUrl
  });
});

app.get("/api/config", (req, res) => {
  const tokenMasked = runtimeBotToken
    ? `${runtimeBotToken.split(":")[0] || "***"}:********`
    : "";

  res.json({
    has_bot_token: Boolean(runtimeBotToken),
    has_chat_id: Boolean(runtimeChatId),
    bot_token_masked: tokenMasked,
    chat_id: runtimeChatId,
    app_url: appUrl
  });
});

app.post("/api/config", (req, res) => {
  const { bot_token, chat_id } = req.body || {};
  if (typeof bot_token === "string") {
    runtimeBotToken = bot_token.trim();
  }
  if (typeof chat_id === "string") {
    runtimeChatId = chat_id.trim();
  }
  res.json({
    success: true,
    message: "Telegram configuration updated successfully",
    has_bot_token: Boolean(runtimeBotToken),
    has_chat_id: Boolean(runtimeChatId),
    chat_id: runtimeChatId
  });
});

app.post("/api/test-telegram", async (req, res) => {
  const { bot_token, chat_id } = req.body || {};
  const token = bot_token || runtimeBotToken;
  const chat = chat_id || runtimeChatId;

  const testMessage = (
    `🔔 *Telegram Alert Verification Test*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━\n` +
    `✅ Your Telegram Bot integration is working properly!\n` +
    `🕒 *Sent at:* ${new Date().toISOString()}\n` +
    `🛍️ You will receive instant order notifications in this chat.`
  );

  const result = await sendTelegramMessage(testMessage, token, chat);
  res.json(result);
});

// Fetch all orders
app.get("/api/orders", async (req, res) => {
  try {
    const { stdout } = await execFileAsync("python3", ["database.py", "list"]);
    // Find the JSON array in stdout
    const jsonStart = stdout.indexOf("[");
    if (jsonStart !== -1) {
      const orders = JSON.parse(stdout.substring(jsonStart));
      return res.json({ success: true, orders });
    }
    res.json({ success: true, orders: [] });
  } catch (err: any) {
    console.error("Error fetching orders via python:", err);
    res.status(500).json({ success: false, error: err.message, orders: [] });
  }
});

// Create an order
app.post("/api/order", async (req, res) => {
  try {
    const {
      customer_name,
      phone_number,
      product_name,
      quantity = 1,
      unit_price = 0,
      total_price = 0,
      notes = "",
      is_telegram_webapp = false,
      telegram_user_id = "",
      telegram_username = ""
    } = req.body;

    if (!customer_name || !phone_number || !product_name) {
      return res.status(400).json({
        success: false,
        error: "Missing required fields: Customer Name, Phone Number, and Product Name are required."
      });
    }

    const qty = Math.max(1, parseInt(quantity, 10) || 1);
    const price = parseFloat(unit_price) || 0;
    const isTg = is_telegram_webapp ? "1" : "0";

    // Call python database.py insert
    const { stdout } = await execFileAsync("python3", [
      "database.py",
      "insert",
      customer_name.toString(),
      phone_number.toString(),
      product_name.toString(),
      qty.toString(),
      price.toString(),
      (notes || "").toString(),
      isTg,
      (telegram_user_id || "").toString(),
      (telegram_username || "").toString()
    ]);

    // Parse inserted record from output
    const jsonStart = stdout.lastIndexOf("{");
    if (jsonStart === -1) {
      throw new Error("Failed to parse order insertion output from Python backend");
    }
    const order = JSON.parse(stdout.substring(jsonStart));

    // Send Telegram alert notification
    const alertMessage = formatTelegramAlert(order);
    const tgResult = await sendTelegramMessage(alertMessage);

    res.status(201).json({
      success: true,
      message: "Order placed successfully!",
      order,
      telegram: tgResult,
      telegram_preview: alertMessage
    });
  } catch (err: any) {
    console.error("Order processing error:", err);
    res.status(500).json({
      success: false,
      error: err.message || "Failed to process order"
    });
  }
});

// Update order status
app.patch("/api/order/:id/status", async (req, res) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    if (!status) {
      return res.status(400).json({ success: false, error: "Status is required" });
    }

    await execFileAsync("python3", [
      "-c",
      `import database; database.update_order_status("${id}", "${status}")`
    ]);

    res.json({ success: true, message: `Order #${id} updated to ${status}` });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    if (fs.existsSync(distPath)) {
      app.use(express.static(distPath));
      app.get("*", (req, res) => {
        res.sendFile(path.join(distPath, "index.html"));
      });
    }
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
