"use client";

import { useState, useEffect } from 'react';

export function useTelegram() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTelegram, setIsTelegram] = useState(false);

  useEffect(() => {
    const checkTelegram = () => {
      try {
        // Check if Telegram WebApp is available
        if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
          console.log('✅ Telegram WebApp detected');
          setIsTelegram(true);
          
          const tg = window.Telegram.WebApp;
          
          // Initialize
          tg.expand();
          tg.ready();
          
          // Try to get user data
          const userData = tg.initDataUnsafe?.user;
          console.log('📱 Telegram user data:', userData);
          
          if (userData) {
            setUser({
              id: userData.id,
              first_name: userData.first_name,
              last_name: userData.last_name || '',
              username: userData.username,
              language_code: userData.language_code,
            });
          } else {
            console.log('❌ No user data found');
            setUser({
              id: 0,
              first_name: "Telegram",
              last_name: "User", 
              username: "telegram_user",
              language_code: "en",
            });
          }
        } else {
          console.log('🌐 Running in browser - using mock data');
          setIsTelegram(false);
          // Mock data for development
          setUser({
            id: 123456789,
            first_name: "John",
            last_name: "Doe",
            username: "johndoe",
            language_code: "en",
          });
        }
      } catch (error) {
        console.error('💥 Error:', error);
        setUser({
          id: 999999,
          first_name: "Error",
          last_name: "User",
          username: "error",
          language_code: "en",
        });
      } finally {
        setLoading(false);
      }
    };

    // Check immediately and also after a short delay
    checkTelegram();
    const timeout = setTimeout(checkTelegram, 500);
    
    return () => clearTimeout(timeout);
  }, []);

  return { user, loading, isTelegram };
}