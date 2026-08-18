'use client'

import { useEffect, useState } from 'react'
import * as streamStore from './streamStore'

// Subscribe React component to module-level stream store.
// Returns the latest snapshot; component re-renders on every notify().
export function useStreamStore() {
    const [snap, setSnap] = useState(() => streamStore.getState())
    useEffect(() => {
        // Sync once in case state changed between initial getState() and subscribe().
        setSnap(streamStore.getState())
        const unsub = streamStore.subscribe(setSnap)
        return unsub
    }, [])
    return snap
}
