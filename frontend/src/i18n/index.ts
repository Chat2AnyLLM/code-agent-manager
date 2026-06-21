import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import zh from './locales/zh.json'

type Language = 'zh' | 'en'

const STORAGE_KEY = 'cam.lang'

const getInitialLanguage = (): Language => {
  if (typeof window !== 'undefined') {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      if (stored === 'zh' || stored === 'en') return stored
    } catch {
      // ignore
    }
  }

  const navigatorLang = typeof navigator !== 'undefined'
    ? navigator.language?.toLowerCase()
    : undefined

  if (navigatorLang?.startsWith('zh')) return 'zh'
  return 'en'
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    zh: { translation: zh },
  },
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
  debug: false,
})

export default i18n
