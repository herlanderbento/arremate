export type Theme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'theme'

export const THEME_INIT_SCRIPT = `(function(){var t;try{t=localStorage.getItem('${THEME_STORAGE_KEY}')}catch(e){}if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'}document.documentElement.dataset.theme=t})()`
