// app/types/telegram.d.ts
declare global {
  interface Window {
    Telegram: {
      WebApp: {
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
            is_premium?: boolean;
            photo_url?: string;
          };
        };
        expand: () => void;
        enableClosingConfirmation: () => void;
        close: () => void;
      };
    };
  }
}

export {};