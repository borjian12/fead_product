// app/components/TelegramLogin.jsx
"use client";

import { useEffect } from 'react';

export function TelegramLogin({ onAuth }) {
  useEffect(() => {
    // Load Telegram widget script
    const script = document.createElement('script');
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute('data-telegram-login', 'YOUR_BOT_USERNAME'); // جایگزین کن
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    
    // Global function for callback
    window.onTelegramAuth = (user) => {
      console.log('Telegram Auth User:', user);
      onAuth(user);
    };

    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
      delete window.onTelegramAuth;
    };
  }, [onAuth]);

  return (
    <div id="telegram-login-container" className="text-center"></div>
  );
}