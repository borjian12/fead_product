"use client";

import { useEffect, useState } from 'react';

export function useTelegramInitData() {
  const [data, setData] = useState({});
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initData = () => {
      try {
        if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
          const tg = window.Telegram.WebApp;
          
          tg.expand();
          tg.ready();
          
          console.log('Telegram WebApp available');
          console.log('initData:', tg.initData);
          console.log('initDataUnsafe:', tg.initDataUnsafe);
          
          // Parse initData
          const initDataString = tg.initData;
          if (initDataString) {
            const firstLayerInitData = Object.fromEntries(
              new URLSearchParams(initDataString)
            );

            const parsedData = {};
            for (const key in firstLayerInitData) {
              try {
                parsedData[key] = JSON.parse(firstLayerInitData[key]);
              } catch {
                parsedData[key] = firstLayerInitData[key];
              }
            }
            
            setData(parsedData);
            setUser(parsedData.user || tg.initDataUnsafe?.user);
          } else {
            // Fallback to initDataUnsafe
            setUser(tg.initDataUnsafe?.user);
          }
        } else {
          console.log('Telegram WebApp not available, using mock data');
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
        console.error('Error parsing Telegram init data:', error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    setTimeout(initData, 100);
  }, []);

  return { data, user, loading };
}