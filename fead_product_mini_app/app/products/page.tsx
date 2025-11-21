"use client";

import { ShoppingBag, Star, MessageSquare, Package } from 'lucide-react';

const products = [
  {
    id: 1,
    name: "Premium Widget",
    description: "High-quality widget with advanced features and lifetime warranty.",
    price: "$49.99",
    rating: 4.8,
    reviews: 124,
    category: "Electronics",
    image: "🛍️"
  },
  {
    id: 2,
    name: "Smart Gadget Pro",
    description: "Innovative gadget with AI capabilities and smart connectivity.",
    price: "$79.99",
    rating: 4.6,
    reviews: 89,
    category: "Tech",
    image: "📱"
  },
  {
    id: 3,
    name: "Eco Solution Kit",
    description: "Environmentally friendly product bundle for sustainable living.",
    price: "$29.99",
    rating: 4.9,
    reviews: 203,
    category: "Home",
    image: "🌱"
  },
  {
    id: 4,
    name: "Wireless Earbuds",
    description: "Crystal clear sound with noise cancellation and 24h battery.",
    price: "$59.99",
    rating: 4.7,
    reviews: 156,
    category: "Audio",
    image: "🎧"
  },
  {
    id: 5,
    name: "Fitness Tracker",
    description: "Track your health metrics with precision and style.",
    price: "$39.99",
    rating: 4.5,
    reviews: 78,
    category: "Fitness",
    image: "⌚"
  },
  {
    id: 6,
    name: "Smart Home Hub",
    description: "Control all your smart devices from one central hub.",
    price: "$99.99",
    rating: 4.8,
    reviews: 167,
    category: "Home",
    image: "🏠"
  }
];

export default function ProductsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <ShoppingBag className="w-8 h-8 text-purple-500" />
            <h1 className="text-4xl font-bold text-gray-900">Our Products</h1>
          </div>
          <p className="text-gray-600 max-w-2xl mx-auto text-lg">
            Discover our amazing products and share your feedback to help us improve.
          </p>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((product) => (
            <div key={product.id} className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-gray-100">
              {/* Product Image/Icon */}
              <div className="text-5xl mb-4 text-center">{product.image}</div>
              
              {/* Product Info */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-bold text-gray-900">{product.name}</h3>
                  <span className="text-lg font-bold text-purple-600">{product.price}</span>
                </div>
                <p className="text-gray-600 text-sm mb-3">{product.description}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    <Star className="w-4 h-4 text-yellow-400" fill="currentColor" />
                    <span className="text-sm font-semibold text-gray-700">{product.rating}</span>
                    <span className="text-sm text-gray-500">({product.reviews})</span>
                  </div>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                    {product.category}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-2">
                <button className="flex-1 bg-purple-500 hover:bg-purple-600 text-white py-2 px-4 rounded-xl transition-colors duration-200 font-medium text-sm flex items-center justify-center space-x-2">
                  <MessageSquare className="w-4 h-4" />
                  <span>Feedback</span>
                </button>
                <button className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 px-4 rounded-xl transition-colors duration-200 font-medium text-sm flex items-center justify-center space-x-2">
                  <Package className="w-4 h-4" />
                  <span>Order</span>
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Products Count */}
        <div className="text-center mt-8 text-gray-500">
          Showing {products.length} products
        </div>
      </div>
    </div>
  );
}