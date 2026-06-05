import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, icon, actions, className }) => {
  return (
    <header className={`w-full ${className || ''}`} role="banner" aria-label={title}>
      <div className="fluid-container">
        <div className="flex items-center justify-between gap-4 mb-4 w-full">
          <div className="flex items-center gap-3 min-w-0">
            {icon && (
              <div
                className="bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center"
                style={{
                  width: 'var(--page-icon-size)',
                  height: 'var(--page-icon-size)',
                  minWidth: 'var(--page-icon-size)'
                }}
                aria-hidden
              >
                {icon}
              </div>
            )}
            <div className="min-w-0">
              <h1
                className="font-semibold text-gray-900 truncate"
                style={{ fontSize: 'var(--fluid-page-title-size)', lineHeight: 'var(--fluid-page-title-line-height)' }}
              >
                {title}
              </h1>
              {subtitle && (
                <p
                  className="text-gray-600 truncate"
                  style={{ fontSize: 'var(--fluid-page-subtitle-size)', lineHeight: 'var(--fluid-page-subtitle-line-height)' }}
                >
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {actions && (
            <div className="flex items-center" style={{ gap: 'var(--fluid-action-gap, 0.5rem)' }}>
              {actions}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default PageHeader
