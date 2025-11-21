"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, User, ShoppingBag, Package, MessageSquare, Star, Menu, X } from "lucide-react";
import { useState, useEffect } from "react";

const navItems = [
  { name: "Home", href: "/", icon: Home },
  { name: "Profile", href: "/profile", icon: User },
  { name: "Products", href: "/products", icon: ShoppingBag },
  { name: "Orders", href: "/orders", icon: Package },
  { name: "Feedback", href: "/feedback", icon: MessageSquare },
];

export default function ModernNavbar() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 10;
      setScrolled(isScrolled);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "bg-white/95 backdrop-blur-xl shadow-lg py-2" : "bg-gradient-to-r from-violet-600 to-purple-500 py-4"}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Top Section */}
          <div className="flex justify-between items-center">
            {/* Logo & Brand */}
            <div className="flex items-center space-x-3">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${scrolled ? "bg-gradient-to-r from-violet-600 to-purple-500" : "bg-white"}`}>
                <Star className={`w-6 h-6 ${scrolled ? "text-white" : "text-violet-600"}`} />
              </div>
              <div className="flex flex-col">
                <span className={`text-xl font-bold ${scrolled ? "text-gray-800" : "text-white"}`}>FeedbackPro</span>
                <span className={`text-xs ${scrolled ? "text-gray-500" : "text-white/80"}`}>Product Excellence</span>
              </div>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex space-x-1 bg-white/20 backdrop-blur-sm rounded-2xl p-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link key={item.name} href={item.href}>
                    <div
                      className={`
                        flex items-center space-x-2 px-4 py-2 rounded-xl
                        transition-all duration-300 ease-in-out cursor-pointer
                        ${isActive 
                          ? "bg-white text-violet-600 shadow-lg" 
                          : "text-white hover:bg-white/20"
                        }
                      `}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="text-sm font-medium">{item.name}</span>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Mobile Menu Button */}
            <button 
              className="md:hidden p-2 rounded-lg"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? (
                <X className={`w-6 h-6 ${scrolled ? "text-gray-800" : "text-white"}`} />
              ) : (
                <Menu className={`w-6 h-6 ${scrolled ? "text-gray-800" : "text-white"}`} />
              )}
            </button>
          </div>

          {/* Bottom Mobile Navigation */}
          <div className={`md:hidden mt-4 transition-all duration-300 ${scrolled ? "opacity-100" : "opacity-90"}`}>
            <div className="flex justify-around bg-white rounded-2xl shadow-lg p-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link key={item.name} href={item.href}>
                    <div
                      className={`
                        flex flex-col items-center justify-center p-2 rounded-xl
                        transition-all duration-300 ease-in-out cursor-pointer min-w-[60px]
                        ${isActive 
                          ? "bg-gradient-to-r from-violet-600 to-purple-500 text-white scale-110" 
                          : "text-gray-600 hover:text-violet-600"
                        }
                      `}
                    >
                      <Icon className="w-5 h-5 mb-1" />
                      <span className="text-xs font-medium">{item.name}</span>
                      {isActive && (
                        <div className="w-1 h-1 bg-white rounded-full mt-1"></div>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Slide-out Menu */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden" onClick={() => setIsMenuOpen(false)}>
          <div className="absolute top-20 right-4 left-4 bg-white rounded-2xl shadow-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="p-4">
              {/* User Profile Section */}
              <div className="flex items-center space-x-3 p-4 bg-gradient-to-r from-violet-600 to-purple-500 rounded-xl text-white mb-4">
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-bold">Welcome Back!</p>
                  <p className="text-sm opacity-80">Product Feedback Expert</p>
                </div>
              </div>
              
              {/* Menu Items */}
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link key={item.name} href={item.href} onClick={() => setIsMenuOpen(false)}>
                    <div
                      className={`
                        flex items-center space-x-3 p-4 rounded-xl mb-2
                        transition-all duration-300 ease-in-out cursor-pointer
                        ${isActive 
                          ? "bg-violet-50 text-violet-600 border-r-4 border-violet-600" 
                          : "text-gray-700 hover:bg-gray-100"
                        }
                      `}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{item.name}</span>
                    </div>
                  </Link>
                );
              })}

              {/* Stats Section */}
              <div className="mt-6 p-4 bg-gray-50 rounded-xl">
                <div className="flex justify-between text-sm">
                  <div className="text-center">
                    <p className="font-bold text-violet-600">24</p>
                    <p className="text-gray-500">Feedbacks</p>
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-violet-600">8</p>
                    <p className="text-gray-500">Products</p>
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-violet-600">12</p>
                    <p className="text-gray-500">Orders</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Spacer for main content */}
      <div className="h-28 md:h-24"></div>
    </>
  );
}