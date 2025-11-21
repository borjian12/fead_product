"use client";

import { useState, useEffect } from 'react';

export function useTelegram() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTelegram, setIsTelegram] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    const checkTelegram = () => {
      if (typeof window === 'undefined') return;

      if (window.Telegram?.WebApp) {
        console.log('✅ Telegram WebApp detected');
        setIsTelegram(true);
        
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        const userData = tg.initDataUnsafe?.user;
        console.log('📱 Raw user data:', userData);
        
        // Check if we have complete user data
        if (userData && userData.id && userData.username) {
          // User is fully authenticated
          setUser({
            id: userData.id,
            first_name: userData.first_name,
            last_name: userData.last_name || '',
            username: userData.username,
            language_code: userData.language_code,
            is_premium: userData.is_premium,
            photo_url: userData.photo_url,
          });
          setNeedsAuth(false);
        } else if (userData && userData.id) {
          // User has limited data (needs auth)
          setUser({
            id: userData.id,
            first_name: userData.first_name || 'User',
            is_limited: true
          });
          setNeedsAuth(true);
        } else {
          // No user data at all
          setNeedsAuth(true);
        }
        
        setLoading(false);
      } else {
        // Development mode
        console.log('🌐 Development mode');
        setIsTelegram(false);
        setUser({
          id: 123456789,
          first_name: "John",
          username: "johndoe",
          language_code: "en",
        });
        setLoading(false);
      }
    };

    checkTelegram();
  }, []);

  return { user, loading, isTelegram, needsAuth };
}