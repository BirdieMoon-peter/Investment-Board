import {useEffect, useRef, useState} from 'react'
// Revision and identity jointly own reads. Retained results belong only to the same security.
export function useSavedIndicators<T>(identity: number, revision: unknown, load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{identity: number; data: T | null; loading: boolean; error: boolean}>({identity, data:null, loading:true, error:false})
  const [retry, setRetry] = useState(0)
  const owner = useRef(0)
  useEffect(() => {
    const version = ++owner.current, c = new AbortController()
    const owns = () => !c.signal.aborted && owner.current === version
    setState(s => ({identity, data:s.identity === identity ? s.data : null, loading:true, error:false}))
    load(c.signal).then(data => {if (owns()) setState({identity,data,loading:false,error:false})})
      .catch(() => {if (owns()) setState(s => ({...s,loading:false,error:true}))})
    return () => c.abort()
  }, [identity, revision, load, retry])
  return { ...state, data: state.identity === identity ? state.data : null, retry: () => setRetry(v => v+1) }
}
