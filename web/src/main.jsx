import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

document.documentElement.dataset.skin = 'clay'
document.fonts?.load('20px "Material Symbols Outlined"', 'home')
  .then(f => { if (f.length) document.documentElement.classList.add('icons') })
  .catch(() => {})
createRoot(document.getElementById('root')).render(<App />)
