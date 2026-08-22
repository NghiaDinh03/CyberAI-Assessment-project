'use client'

import { useSyncExternalStore } from 'react'
import * as streamStore from './streamStore'

// Subscribe React component to module-level stream store via React's official useSyncExternalStore.
// This prevents infinite render loops, cascading setState depth warnings, and concurrent tearing.
export function useStreamStore() {
    return useSyncExternalStore(
        streamStore.subscribe,
        streamStore.getState,
        streamStore.getServerSnapshot
    )
}
