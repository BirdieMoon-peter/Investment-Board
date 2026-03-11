interface StatusMessageProps {
  tone?: 'info' | 'error'
  message: string
}

export function StatusMessage({ tone = 'info', message }: StatusMessageProps) {
  return <p role={tone === 'error' ? 'alert' : 'status'}>{message}</p>
}
