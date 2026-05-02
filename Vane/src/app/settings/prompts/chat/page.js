'use client'

import PromptManager from '@/components/PromptManager'

export default function ChatPromptsPage() {
    return (
        <PromptManager
            group="chat"
            titleKey="prompts.chatTitle"
            descKey="prompts.chatDesc"
        />
    )
}
