import { useState, useEffect } from "react";
import { TelegramBanner } from "./components/TelegramBanner";
import { OrderForm } from "./components/OrderForm";
import { OrderSuccessModal } from "./components/OrderSuccessModal";
import { OrdersListModal } from "./components/OrdersListModal";
import { BotIntegrationModal } from "./components/BotIntegrationModal";
import { Order, TelegramUser } from "./types";
import { ShoppingBag, Database, Bot, ShieldCheck, Sparkles } from "lucide-react";

export default function App() {
  const [isInsideTelegram, setIsInsideTelegram] = useState(false);
  const [tgUser, setTgUser] = useState<TelegramUser | null>(null);
  const [platform, setPlatform] = useState("web");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Modals state
  const [placedOrder, setPlacedOrder] = useState<Order | null>(null);
  const [telegramResult, setTelegramResult] = useState<any>(null);
  const [telegramPreview, setTelegramPreview] = useState<string>("");
  const [showOrdersModal, setShowOrdersModal] = useState(false);
  const [showBotModal, setShowBotModal] = useState(false);
  const [orderCount, setOrderCount] = useState<number>(0);

  // Initialize Telegram WebApp SDK
  useEffect(() => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      // Signal ready and expand to fill available height
      try {
        tg.ready();
        tg.expand();
      } catch (e) {
        console.warn("Telegram WebApp ready error:", e);
      }

      // Check if initData exists, indicating actual Telegram context
      const hasInitData = Boolean(tg.initData && tg.initData.length > 0);
      const detectedPlatform = tg.platform || "web";

      // If opened inside Telegram, platform is usually 'ios', 'android', 'tdesktop', 'macos', etc.
      const isTgClient = hasInitData || (detectedPlatform !== "unknown" && detectedPlatform !== "web");

      setIsInsideTelegram(isTgClient);
      setPlatform(detectedPlatform);

      if (tg.initDataUnsafe?.user) {
        setTgUser(tg.initDataUnsafe.user);
      }
    }

    // Pre-fetch count of existing orders
    fetch("/api/orders")
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.orders)) {
          setOrderCount(data.orders.length);
        }
      })
      .catch((err) => console.warn("Could not fetch orders count:", err));
  }, []);

  const handleOrderSubmit = async (formData: {
    customer_name: string;
    phone_number: string;
    product_name: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    notes: string;
  }) => {
    setIsSubmitting(true);
    try {
      const payload = {
        ...formData,
        is_telegram_webapp: isInsideTelegram,
        telegram_user_id: tgUser?.id ? String(tgUser.id) : "",
        telegram_username: tgUser?.username || ""
      };

      const response = await fetch("/api/order", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Failed to submit order.");
      }

      // Haptic feedback if in Telegram
      if (typeof window !== "undefined" && window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
      }

      setPlacedOrder(data.order);
      setTelegramResult(data.telegram);
      setTelegramPreview(data.telegram_preview || "");
      setOrderCount((prev) => prev + 1);
    } catch (err: any) {
      console.error("Order submission error:", err);
      alert(`Order placement error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* Top Application Header */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-sm sm:text-base leading-tight text-slate-900">
                Telegram Storefront
              </h1>
              <p className="text-[11px] text-slate-500 hidden sm:block">
                E-Commerce Orders + SQLite & Telegram Bot Alerting
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              id="btn-nav-orders"
              onClick={() => setShowOrdersModal(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer"
            >
              <Database className="w-3.5 h-3.5 text-blue-600" />
              <span>Orders</span>
              {orderCount > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-blue-100 text-blue-800 text-[10px] font-bold">
                  {orderCount}
                </span>
              )}
            </button>

            <button
              type="button"
              id="btn-nav-bot-setup"
              onClick={() => setShowBotModal(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white shadow-xs transition-colors cursor-pointer"
            >
              <Bot className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Bot & Deployment</span>
              <span className="sm:hidden">Bot</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-6 space-y-5">
        {/* Telegram WebApp Auto-Detection Banner */}
        <TelegramBanner
          isInsideTelegram={isInsideTelegram}
          tgUser={tgUser}
          platform={platform}
          onOpenBotGuide={() => setShowBotModal(true)}
        />

        {/* Primary Order Form */}
        <OrderForm
          isInsideTelegram={isInsideTelegram}
          tgUser={tgUser}
          onSubmitOrder={handleOrderSubmit}
          isSubmitting={isSubmitting}
        />

        {/* System Architecture Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3.5 bg-white rounded-xl border border-slate-200/80 shadow-2xs">
            <div className="text-blue-600 font-bold text-xs flex items-center gap-1.5 mb-1">
              <ShoppingBag className="w-3.5 h-3.5" /> Telegram Mini App SDK
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Auto-detects Telegram context, themes, and pre-populates user data with native MainButton support.
            </p>
          </div>

          <div className="p-3.5 bg-white rounded-xl border border-slate-200/80 shadow-2xs">
            <div className="text-emerald-600 font-bold text-xs flex items-center gap-1.5 mb-1">
              <Database className="w-3.5 h-3.5" /> Python SQLite Storage
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Persistent storage in <code className="text-slate-700 bg-slate-100 px-1 py-0.5 rounded">orders.db</code> via Python <code className="text-slate-700 bg-slate-100 px-1 py-0.5 rounded">database.py</code>.
            </p>
          </div>

          <div className="p-3.5 bg-white rounded-xl border border-slate-200/80 shadow-2xs">
            <div className="text-indigo-600 font-bold text-xs flex items-center gap-1.5 mb-1">
              <Bot className="w-3.5 h-3.5" /> Real-Time Telegram Alerts
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Instant markdown order notifications dispatched to your specified Telegram Group or Channel.
            </p>
          </div>
        </div>
      </main>

      {/* Success Receipt Modal */}
      {placedOrder && (
        <OrderSuccessModal
          order={placedOrder}
          telegramResult={telegramResult}
          telegramPreview={telegramPreview}
          isInsideTelegram={isInsideTelegram}
          onClose={() => setPlacedOrder(null)}
        />
      )}

      {/* Orders Database Modal */}
      <OrdersListModal
        isOpen={showOrdersModal}
        onClose={() => setShowOrdersModal(false)}
      />

      {/* Bot & Python Deployment Modal */}
      <BotIntegrationModal
        isOpen={showBotModal}
        onClose={() => setShowBotModal(false)}
      />
    </div>
  );
}
