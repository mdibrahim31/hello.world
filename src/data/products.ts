import { Product } from "../types";

export const CATALOG_PRODUCTS: Product[] = [
  {
    id: "prod-1",
    name: "Classic Organic Cotton T-Shirt",
    price: 24.99,
    category: "Apparel",
    description: "100% premium combed organic cotton with relaxed fit.",
    icon: "Shirt",
    badge: "Best Seller"
  },
  {
    id: "prod-2",
    name: "Pro Wireless Noise-Cancelling Earbuds",
    price: 59.99,
    category: "Electronics",
    description: "Crystal clear audio, active noise cancellation, 30h battery.",
    icon: "Headphones",
    badge: "Popular"
  },
  {
    id: "prod-3",
    name: "Ultra-Lightweight Canvas Daypack",
    price: 45.00,
    category: "Bags & Gear",
    description: "Water-resistant commuter backpack with 16-inch laptop compartment.",
    icon: "Backpack"
  },
  {
    id: "prod-4",
    name: "Ceramic Matte Brew Mug 350ml",
    price: 18.50,
    category: "Home & Living",
    description: "Artisan stoneware mug designed for coffee and matcha lovers.",
    icon: "Coffee"
  },
  {
    id: "prod-5",
    name: "Smart AMOLED Fitness Tracker",
    price: 89.90,
    category: "Wearables",
    description: "Heart rate, SpO2, sleep tracking, and 5 ATM water resistance.",
    icon: "Watch",
    badge: "New"
  }
];
