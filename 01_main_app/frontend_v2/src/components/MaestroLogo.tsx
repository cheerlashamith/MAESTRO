interface MaestroLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  subtitle?: string;
  className?: string;
  onClick?: () => void;
}

export default function MaestroLogo({
  size = 'md',
  showText = true,
  subtitle = 'ENGINE',
  className = '',
  onClick
}: MaestroLogoProps) {
  const dimensions = {
    sm: { iconSize: 32, titleSize: '1.1rem', subSize: '0.6rem' },
    md: { iconSize: 42, titleSize: '1.35rem', subSize: '0.65rem' },
    lg: { iconSize: 64, titleSize: '1.85rem', subSize: '0.75rem' },
    xl: { iconSize: 84, titleSize: '2.4rem', subSize: '0.85rem' },
  }[size];

  return (
    <div 
      className={`maestro-brand-badge ${className}`}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: size === 'sm' ? '0.6rem' : '0.85rem',
        cursor: onClick ? 'pointer' : 'default',
        userSelect: 'none'
      }}
    >
      <div 
        className="maestro-logo-box"
        style={{
          width: dimensions.iconSize,
          height: dimensions.iconSize,
          borderRadius: size === 'sm' ? '10px' : size === 'md' ? '12px' : '18px',
          background: 'linear-gradient(135deg, #5227c7 0%, #7040f7 50%, #ff6d34 100%)',
          boxShadow: '0 8px 20px -4px rgba(82, 39, 199, 0.45), 0 4px 10px -2px rgba(255, 109, 52, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden',
          border: '1.5px solid rgba(255, 255, 255, 0.35)',
          transition: 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease',
          flexShrink: 0
        }}
      >
        {/* Shimmer Ambient Aura */}
        <div 
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.4) 0%, transparent 70%)',
            pointerEvents: 'none'
          }}
        />

        {/* Vector SVG Emblem: Conductor Baton, Neural Spark & Harmonic Waves */}
        <svg 
          width={Math.round(dimensions.iconSize * 0.72)} 
          height={Math.round(dimensions.iconSize * 0.72)} 
          viewBox="0 0 40 40" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Harmonic Waveform Arc */}
          <path 
            d="M5 21C8 14 12 11 16 19C19 25 23 27 27 21C30 16 34 17 36 21" 
            stroke="#FFFFFF" 
            strokeWidth="2.4" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            opacity="0.85" 
          />
          {/* Conductor Baton */}
          <path 
            d="M10 32L28 10" 
            stroke="#ff6d34" 
            strokeWidth="3.2" 
            strokeLinecap="round" 
          />
          <path 
            d="M10 32L14 28" 
            stroke="#FFFFFF" 
            strokeWidth="4" 
            strokeLinecap="round" 
          />
          {/* Central AI Neural Spark */}
          <circle cx="21" cy="18" r="3.5" fill="#FFFFFF" />
          <circle cx="21" cy="18" r="1.8" fill="#ff6d34" />
          {/* Constellation Nodes */}
          <circle cx="28" cy="10" r="2.2" fill="#FFFFFF" />
          <circle cx="15" cy="13" r="1.8" fill="#FFFFFF" opacity="0.9" />
          <circle cx="27" cy="25" r="1.8" fill="#FFFFFF" opacity="0.9" />
        </svg>
      </div>

      {showText && (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span 
              className="brand-title"
              style={{
                fontFamily: "'Libre Baskerville', Georgia, serif",
                fontSize: dimensions.titleSize,
                fontWeight: 700,
                color: '#1e1438',
                letterSpacing: '-0.02em',
                lineHeight: 1.1
              }}
            >
              MAESTRO
            </span>
            {subtitle && (
              <span 
                className="brand-sub-badge"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: dimensions.subSize,
                  fontWeight: 700,
                  padding: '0.15rem 0.45rem',
                  background: 'rgba(82, 39, 199, 0.08)',
                  color: '#5227c7',
                  border: '1px solid rgba(82, 39, 199, 0.25)',
                  borderRadius: '4px',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase'
                }}
              >
                {subtitle}
              </span>
            )}
          </div>
          {size === 'xl' && (
            <span style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '0.25rem' }}>
              Autonomous Multi-Agent Video Orchestration
            </span>
          )}
        </div>
      )}
    </div>
  );
}
