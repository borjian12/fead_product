"use client";

import { useTelegram } from './hooks/useTelegram';
import { User, Crown, Shield, LogIn } from 'lucide-react';

// تعریف نوع در همین فایل
interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
  is_limited?: boolean;
}

export default function HomePage() {
  const { user, loading, isTelegram, needsAuth } = useTelegram();
  
  // type assertion برای user
  const typedUser = user as TelegramUser | null;

  const handleTelegramAuth = (authUser: TelegramUser) => {
    console.log('Authenticated user:', authUser);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-300 rounded w-48 mx-auto mb-4"></div>
              <div className="h-4 bg-gray-300 rounded w-64 mx-auto"></div>
            </div>
            <p className="text-gray-500 mt-4">Connecting to Telegram...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        
        {/* User Info Card */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-teal-500 rounded-full flex items-center justify-center">
                {typedUser?.photo_url ? (
                  <img src={typedUser.photo_url} alt="Profile" className="w-16 h-16 rounded-full" />
                ) : (
                  <User className="w-8 h-8 text-white" />
                )}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {typedUser?.first_name ? `Hello, ${typedUser.first_name}!` : 'Welcome!'}
                </h1>
                
                {typedUser?.username ? (
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-gray-600">@{typedUser.username}</span>
                    {typedUser?.is_premium && (
                      <Crown className="w-4 h-4 text-yellow-500" fill="currentColor" />
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500 mt-1">Limited access</p>
                )}
              </div>
            </div>
            
            <div className="text-right">
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                isTelegram ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
              }`}>
                {isTelegram ? 'Telegram Connected' : 'Development Mode'}
              </div>
              {typedUser?.id && typedUser.id > 0 && (
                <div className="text-xs text-gray-400 mt-1">ID: {typedUser.id}</div>
              )}
            </div>
          </div>

          {/* بقیه کد بدون تغییر... */}
        </div>
      </div>
    </div>
  );
}