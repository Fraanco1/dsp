import React from 'react'
import './Header.css'

export default function Header({ backendOnline }) {
  return (
    <header className="header">
      <span className="header-logo">DSP</span>
      <span className="header-title">Satellite Soil Analysis — Argentine Pampas</span>
      <span className={`header-status ${backendOnline ? 'online' : 'offline'}`}>
        {backendOnline ? 'Backend online' : 'Backend offline'}
      </span>
    </header>
  )
}
