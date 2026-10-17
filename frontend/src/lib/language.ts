import { useState } from 'react';

export type Language = 'en' | 'pt-BR';

const STORAGE_KEY = 'music2chart-language';

function getInitialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'en' || saved === 'pt-BR') return saved;
  } catch {
    // Storage can be unavailable in private or restricted browsing contexts.
  }
  return navigator.language.toLowerCase().startsWith('pt') ? 'pt-BR' : 'en';
}

export function useLanguage(): [Language, (language: Language) => void] {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);
  const setLanguage = (next: Language): void => {
    setLanguageState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Keep the selection for this session when storage is unavailable.
    }
  };
  return [language, setLanguage];
}
