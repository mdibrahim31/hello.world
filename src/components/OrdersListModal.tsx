import { useState, useEffect } from "react";
import { Order } from "../types";
import { Database, RefreshCw, X, Send, Globe, CheckCircle2, Clock, Truck, Ban, AlertTriangle } from "lucide-react";

interface OrdersListModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OrdersListModal({ isOpen, onClose }: OrdersListModalProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchOrders = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/orders");
      const data = await res.json();
      if (data.success) {
        setOrders(data.orders || []);
      } else {
        setError(data.error || "Failed to load orders");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load orders");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchOrders();
    }
  }, [isOpen]);

  const handleUpdateStatus = async (orderId: number, newStatus: string) => {
    setUpdatingId(orderId);
    try {
      const res = await fetch(`/api/order/${orderId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      const data = await res.json();
      if (data.success) {
        setOrders((prev) =>
          prev.map((o) => (o.id === orderId ? { ...o, status: newStatus as any } : o))
        );
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUpdatingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      id="orders-list-modal-overlay"
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
    >
      <div
        id="orders-list-dialog"
        className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-200 my-8 max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                SQLite Orders Database
              </h3>
              <p className="text-xs text-slate-500">
                Live records stored in <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">orders.db</code> via Python Backend
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              id="btn-refresh-orders"
              onClick={fetchOrders}
              disabled={isLoading}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              title="Refresh database records"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              type="button"
              id="btn-close-orders-modal"
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Orders Table or Empty State */}
        <div className="flex-1 overflow-y-auto pr-1">
          {isLoading && orders.length === 0 ? (
            <div className="py-12 text-center text-slate-500 space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
              <p className="text-xs">Querying SQLite database via Python...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : orders.length === 0 ? (
            <div className="py-12 text-center text-slate-500 space-y-2">
              <Database className="w-8 h-8 mx-auto text-slate-300" />
              <p className="text-sm font-semibold text-slate-700">No orders placed yet</p>
              <p className="text-xs text-slate-400">
                Use the order form to submit your first test order!
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {orders.map((ord) => {
                const isTg = Boolean(ord.is_telegram_webapp);
                return (
                  <div key={ord.id} className="py-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-bold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded">
                          {ord.order_number}
                        </span>
                        <span className="font-semibold text-slate-800">
                          {ord.customer_name}
                        </span>
                        <span className="text-slate-500">
                          ({ord.phone_number})
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${
                            isTg
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {isTg ? (
                            <>
                              <Send className="w-2.5 h-2.5" /> Mini App
                            </>
                          ) : (
                            <>
                              <Globe className="w-2.5 h-2.5" /> Web
                            </>
                          )}
                        </span>
                      </div>

                      <div className="text-slate-600">
                        <strong>{ord.product_name}</strong> × {ord.quantity} pc
                        {ord.quantity > 1 ? "s" : ""} •{" "}
                        <span className="font-semibold text-slate-900">
                          ${Number(ord.total_price || 0).toFixed(2)}
                        </span>
                        {ord.notes && (
                          <span className="text-slate-400 italic ml-2">
                            "{ord.notes}"
                          </span>
                        )}
                      </div>

                      <div className="text-[11px] text-slate-400">
                        Created: {ord.created_at || "Just now"}
                      </div>
                    </div>

                    {/* Status Dropdown */}
                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        aria-label="Order Status"
                        value={ord.status}
                        disabled={updatingId === ord.id}
                        onChange={(e) => handleUpdateStatus(ord.id, e.target.value)}
                        className={`text-xs font-semibold px-2.5 py-1.5 rounded-lg border focus:outline-none transition-colors cursor-pointer ${
                          ord.status === "confirmed"
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : ord.status === "shipped"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : ord.status === "cancelled"
                            ? "bg-rose-50 text-rose-700 border-rose-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        <option value="pending">⏳ Pending</option>
                        <option value="confirmed">✓ Confirmed</option>
                        <option value="shipped">🚚 Shipped</option>
                        <option value="cancelled">✕ Cancelled</option>
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 pt-3 flex items-center justify-between text-xs text-slate-500">
          <span>Total Orders: {orders.length}</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-xl transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
