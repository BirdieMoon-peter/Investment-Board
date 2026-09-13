interface StatusMessageProps {
  tone?: 'info' | 'warning' | 'error'
  message: string
}

export function StatusMessage({ tone = 'info', message }: StatusMessageProps) {
  return (
    <p
      className={`status-message status-message--${tone}`}
      role={tone === 'error' || tone === 'warning' ? 'alert' : 'status'}
    >
      {message}
    </p>
  )
}
