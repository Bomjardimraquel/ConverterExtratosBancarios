import React from 'react';
import { Landmark } from 'lucide-react';

export default function Header() {
  return (
    <header style={{
      background: 'linear-gradient(135deg, #1a0a0a 0%, #2d1010 50%, #C53678 100%)',
      padding: '0 2rem',
      height: 64,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 2px 20px rgba(197,54,120,0.25)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: 'linear-gradient(135deg, #FF5841, #C53678)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(255,88,65,0.4)',
        }}>
          <Landmark size={20} color="#fff" strokeWidth={1.8} />
        </div>
        <div>
          <div style={{
            fontFamily: 'Open Sans, sans-serif',
            fontWeight: 800, fontSize: '1.1rem',
            color: '#fff', letterSpacing: '-0.01em',
          }}>ExtratoConverter</div>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.08em' }}>
            GESTÃO CONTÁBIL
          </div>
        </div>
      </div>
      <div style={{
        fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)',
        fontFamily: 'Open Sans, sans-serif',
      }}>
        Dados processados localmente
      </div>
    </header>
  );
}