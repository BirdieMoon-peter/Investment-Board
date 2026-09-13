import { Component, type ReactNode } from 'react'

// A rejected screen import must not take down the surrounding watchlist or header.
// Closing/back navigation unmounts this entrance; reloading can fetch a fresh chunk.
export class WorkspaceLoadBoundary extends Component<{
  children: ReactNode
  fallback: ReactNode
}, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
