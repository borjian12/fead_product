// app/types/index.ts
export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

export interface UseTelegramReturn {
  user: TelegramUser | null;
  loading: boolean;
  isTelegram: boolean;
  needsAuth: boolean;
}