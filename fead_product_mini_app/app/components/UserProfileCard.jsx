// app/components/UserProfileCard.jsx
'use client';

import { User, Crown, Globe } from 'lucide-react';
import { useTelegramUser } from '../hooks/useTelegramUser';

export function UserProfileCard() {
  const { user, loading } = useTelegramUser();

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 animate-pulse">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-gray-300 rounded-full"></div>
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-gray-300 rounded w-3/4"></div>
            <div className="h-3 bg-gray-300 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-6 text-center">
        <User className="w-12 h-12 text-yellow-500 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-yellow-800 mb-2">User Not Found</h3>
        <p className="text-yellow-600">Please open this app from Telegram</p>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl shadow-lg p-6 text-white">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
            {user.photoUrl ? (
              <img 
                src={user.photoUrl} 
                alt={`${user.firstName}'s photo`}
                className="w-16 h-16 rounded-full"
              />
            ) : (
              <User className="w-8 h-8 text-white" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-bold">
              {user.firstName} {user.lastName}
            </h2>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-sm opacity-90">@{user.username}</span>
              {user.isPremium && (
                <Crown className="w-4 h-4 text-yellow-300" fill="currentColor" />
              )}
            </div>
          </div>
        </div>
        
        <div className="text-right">
          <div className="flex items-center space-x-1 justify-end">
            <Globe className="w-4 h-4 opacity-70" />
            <span className="text-sm uppercase">{user.languageCode}</span>
          </div>
          <div className="text-xs opacity-70 mt-1">ID: {user.id}</div>
        </div>
      </div>
    </div>
  );
}