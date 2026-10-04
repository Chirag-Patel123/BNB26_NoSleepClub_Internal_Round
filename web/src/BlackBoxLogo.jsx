import React from 'react'

/**
 * BlackBoxCube - The canonical 3D isometric Black Box cube mark.
 * Rendered using vector geometry with crisp dividing Y seams.
 */
export const BlackBoxCube = ({
  size = 20,
  color = '#000000',
  seamColor = '#ffffff',
  className = '',
  style = {}
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={`bb-cube ${className}`}
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Black Box Cube Logo"
  >
    {/* 3D Isometric Cube Hexagon Base */}
    <polygon points="50,11 84,30.5 84,69.5 50,89 16,69.5 16,30.5" fill={color} />
    {/* Dividing Y Seam separating top, left, and right faces */}
    <path
      d="M50,50 L16,30.5 M50,50 L84,30.5 M50,50 L50,89"
      stroke={seamColor}
      strokeWidth="2.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

/**
 * BlackBoxBadge - Rounded cream badge container containing the 3D Black Box cube,
 * matching the Social Avatar and UI elements in the brand portfolio.
 */
export const BlackBoxBadge = ({
  size = 28,
  cubeSize = 18,
  badgeColor = '#FFF1CF',
  borderColor = 'rgba(255, 241, 207, 0.4)',
  radius = 7,
  className = '',
  style = {}
}) => (
  <div
    className={`bb-badge ${className}`}
    style={{
      width: size,
      height: size,
      backgroundColor: badgeColor,
      border: `1px solid ${borderColor}`,
      borderRadius: radius,
      display: 'grid',
      placeItems: 'center',
      flexShrink: 0,
      boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
      ...style
    }}
  >
    <BlackBoxCube size={cubeSize} color="#000000" seamColor="#ffffff" />
  </div>
)

/**
 * BlackBoxBrand - The primary brand lockup featuring:
 * [ 3D Black Box Cube ] BLACK BOX · WEB AI AGENT
 */
export const BlackBoxBrand = ({ showTag = true, compact = false }) => (
  <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
    <BlackBoxBadge size={30} cubeSize={19} />
    <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="brand-name" style={{ letterSpacing: '0.04em', fontWeight: 800 }}>BLACK BOX</span>
        {showTag && (
          <span
            className="brand-tag mono"
            style={{
              fontSize: '9px',
              padding: '1px 6px',
              borderRadius: '3px',
              background: 'rgba(255, 241, 207, 0.08)',
              color: '#FFF1CF',
              border: '1px solid rgba(255, 241, 207, 0.25)',
              letterSpacing: '0.12em'
            }}
          >
            WEB AI AGENT
          </span>
        )}
      </div>
      {!compact && (
        <span style={{ fontSize: '9px', color: 'var(--mu)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>
          AGENT RECORDER &amp; CAUSAL DEBUGGER
        </span>
      )}
    </div>
  </div>
)

export default BlackBoxBrand
